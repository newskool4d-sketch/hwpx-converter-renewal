"""COM-free JSON command line for the optional kordoc document engine.

The conversion CLI remains independent. Document edits are previews unless
``--apply`` and a separate output path are both supplied.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import math
from pathlib import Path
import sys
from typing import TextIO


EXIT_CODES = {"success": 0, "partial": 2, "error": 1, "cancelled": 130}


class _ArgumentError(ValueError):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise _ArgumentError(message)


def _positive_timeout(value: str) -> float:
    try:
        timeout = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timeout must be a positive number") from exc
    if not math.isfinite(timeout) or timeout <= 0:
        raise argparse.ArgumentTypeError("timeout must be a finite positive number")
    return timeout


def _positive_page(value: str) -> int:
    try:
        page = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("page must be a positive integer") from exc
    if page < 1:
        raise argparse.ArgumentTypeError("page must be a positive integer")
    return page


def _common_options(parser: argparse.ArgumentParser, *, defaults: bool) -> None:
    default = None if defaults else argparse.SUPPRESS
    parser.add_argument("--package-dir", default=default, help="Installed kordoc package directory")
    parser.add_argument("--node-path", default=default, help="Node.js executable")
    parser.add_argument(
        "--timeout", type=_positive_timeout, default=120 if defaults else argparse.SUPPRESS,
        help="Engine timeout in seconds (default: 120)",
    )
    parser.add_argument("--report", default=default, help="Save JSON to a new file (never overwrite)")


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(description=__doc__)
    _common_options(parser, defaults=True)
    commands = parser.add_subparsers(dest="command", required=True)
    for action in ("diagnose", "parse", "compare", "validate", "fields", "profile", "lint", "fill", "patch", "render"):
        command = commands.add_parser(action)
        _common_options(command, defaults=False)
        if action == "compare":
            command.add_argument("before")
            command.add_argument("after")
        elif action != "diagnose":
            command.add_argument("source")
        if action in {"fill", "patch"}:
            control_option = "--values-file" if action == "fill" else "--markdown-file"
            command.add_argument(control_option, required=True)
            command.add_argument("--output", help="New HWPX path; required with --apply")
            command.add_argument("--apply", action="store_true", help="Write the new document instead of previewing")
        elif action == "render":
            command.add_argument("--page", type=_positive_page, default=1)
    return parser


def _error(action: str | None, code: str, message: str, *, status: str = "error", data=None) -> dict:
    return {
        "ok": False, "status": status, "action": action, "data": data,
        "warnings": [], "error": {"code": code, "message": message},
    }


def _request_options(args: argparse.Namespace) -> dict:
    if args.command == "diagnose":
        return {}
    if args.command == "compare":
        return {"before": args.before, "after": args.after}
    options = {"path": args.source}
    if args.command in {"fill", "patch"}:
        if args.apply and not args.output:
            raise _ArgumentError("--apply requires --output with a new HWPX file path")
        control_key = "values_file" if args.command == "fill" else "markdown_file"
        options.update({control_key: getattr(args, control_key), "output": args.output, "dry_run": not args.apply})
    elif args.command == "render":
        options["page"] = args.page
    return options


def _open_report(args: argparse.Namespace) -> TextIO | None:
    if not args.report:
        return None
    report = Path(args.report).expanduser().resolve()
    # Include the requested output even during previews, so a report can never
    # occupy a future document path. resolve() also catches relative aliases.
    for name in ("source", "before", "after", "values_file", "markdown_file", "output"):
        path = getattr(args, name, None)
        if path and report == Path(path).expanduser().resolve():
            raise _ArgumentError("--report must differ from all input, control, and output paths")
    # Open the original path with O_EXCL via 'x'. This rejects existing files,
    # dangling symlinks, and races instead of following a resolved symlink.
    return Path(args.report).expanduser().open("x", encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None, *, client=None, stdout: TextIO | None = None) -> int:
    """Run once, returning an exit code; ``client`` supports request(action, **kwargs)."""
    stream = stdout if stdout is not None else sys.stdout
    args = None
    report = None
    try:
        with contextlib.redirect_stdout(stream):
            args = build_parser().parse_args(argv)
        options = _request_options(args)
        report = _open_report(args)
    except SystemExit as exc:
        return int(exc.code or 0)  # argparse help
    except _ArgumentError as exc:
        result = _error(getattr(args, "command", None), "invalid_arguments", str(exc))
    except (OSError, ValueError) as exc:
        result = _error(getattr(args, "command", None), "report_unavailable", str(exc))
    else:
        try:
            if client is None:
                from kordoc_client import KordocClient

                client = KordocClient(package_dir=args.package_dir, node_path=args.node_path, timeout=args.timeout)
            result = client.request(args.command, **options)
            if not isinstance(result, dict) or result.get("status") not in EXIT_CODES:
                result = _error(args.command, "invalid_response", "Document engine returned an invalid response")
        except KeyboardInterrupt:
            result = _error(args.command, "cancelled", "Operation cancelled", status="cancelled")
        except ImportError as exc:
            result = _error(args.command, "dependency_unavailable", str(exc))
        except Exception as exc:
            result = _error(args.command, "backend_error", str(exc))

    try:
        try:
            encoded = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        except (TypeError, ValueError):
            result = _error(getattr(args, "command", None), "invalid_response", "Document engine response is not valid JSON")
            encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if report is not None:
            try:
                report.write(encoded)
                report.flush()
            except OSError as exc:
                result = _error(
                    getattr(args, "command", None), "report_write_failed", str(exc),
                    data={"operation_result": result},
                )
                encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        stream.write(encoded)
    finally:
        if report is not None:
            report.close()
    return EXIT_CODES[result["status"]]


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
