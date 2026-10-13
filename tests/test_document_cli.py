from __future__ import annotations

import importlib
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import document_cli


class FakeClient:
    def __init__(self, status="success", error=None):
        self.status = status
        self.error = error
        self.calls = []

    def request(self, action, **kwargs):
        self.calls.append((action, kwargs))
        if self.error is not None:
            raise self.error
        return {
            "ok": self.status == "success", "status": self.status, "action": action,
            "data": {"title": "검사 결과"}, "warnings": [],
            "error": None if self.status == "success" else {"code": self.status, "message": self.status},
        }


class DocumentCliTests(unittest.TestCase):
    def run_cli(self, argv, client=None):
        stream = io.StringIO()
        client = client if client is not None else FakeClient()
        code = document_cli.main(argv, client=client, stdout=stream)
        return code, json.loads(stream.getvalue()), client

    def test_read_commands_forward_the_source_without_com(self):
        for action in ("parse", "validate", "fields", "profile", "lint"):
            with self.subTest(action=action):
                code, result, client = self.run_cli([action, "한글 경로.hwpx"])
                self.assertEqual(code, 0)
                self.assertEqual(result["data"]["title"], "검사 결과")
                self.assertEqual(client.calls, [(action, {"path": "한글 경로.hwpx"})])

    def test_compare_diagnose_and_render_dispatch(self):
        cases = [
            (["compare", "before.hwpx", "after.hwp"], "compare", {"before": "before.hwpx", "after": "after.hwp"}),
            (["diagnose"], "diagnose", {}),
            (["render", "source.hwpx", "--page", "3"], "render", {"path": "source.hwpx", "page": 3}),
            (["render", "source.hwpx"], "render", {"path": "source.hwpx", "page": 1}),
        ]
        for argv, action, options in cases:
            with self.subTest(argv=argv):
                code, _, client = self.run_cli(argv)
                self.assertEqual(code, 0)
                self.assertEqual(client.calls, [(action, options)])

    def test_mutations_preview_by_default_and_apply_requires_output(self):
        for action, flag, key in (("fill", "--values-file", "values_file"), ("patch", "--markdown-file", "markdown_file")):
            argv = [action, "source.hwpx", flag, "control.txt"]
            with self.subTest(action=action):
                code, _, client = self.run_cli(argv)
                self.assertEqual(code, 0)
                self.assertEqual(client.calls[0], (action, {"path": "source.hwpx", key: "control.txt", "output": None, "dry_run": True}))
                code, result, client = self.run_cli(argv + ["--apply"])
                self.assertEqual(code, 1)
                self.assertEqual(result["error"]["code"], "invalid_arguments")
                self.assertEqual(client.calls, [])
                code, _, client = self.run_cli(argv + ["--apply", "--output", "new.hwpx"])
                self.assertEqual(code, 0)
                self.assertFalse(client.calls[0][1]["dry_run"])
                self.assertEqual(client.calls[0][1]["output"], "new.hwpx")

    def test_exit_codes_preserve_partial_error_and_cancellation(self):
        for status, expected in document_cli.EXIT_CODES.items():
            with self.subTest(status=status):
                code, result, _ = self.run_cli(["diagnose"], FakeClient(status))
                self.assertEqual(code, expected)
                self.assertEqual(result["status"], status)
                self.assertEqual(result["ok"], status == "success")

    def test_exception_and_interrupt_are_json(self):
        for exception, status, expected in ((RuntimeError("failed"), "error", 1), (KeyboardInterrupt(), "cancelled", 130)):
            with self.subTest(exception=type(exception).__name__):
                code, result, _ = self.run_cli(["diagnose"], FakeClient(error=exception))
                self.assertEqual((code, result["status"]), (expected, status))

    def test_argument_errors_never_call_engine(self):
        cases = [[], ["unknown"], ["parse"], ["render", "x", "--page", "0"],
                 ["--timeout", "nan", "diagnose"], ["diagnose", "--timeout", "0"],
                 ["--timeout", "inf", "diagnose"], ["fill", "source.hwpx"]]
        for argv in cases:
            with self.subTest(argv=argv):
                code, result, client = self.run_cli(argv)
                self.assertEqual(code, 1)
                self.assertEqual(result["error"]["code"], "invalid_arguments")
                self.assertEqual(client.calls, [])

    def test_report_is_json_equal_to_stdout_and_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "한글 보고서.json"
            code, result, _ = self.run_cli(["--report", str(report), "diagnose"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(report.read_text(encoding="utf-8")), result)
            original = report.read_bytes()
            code, result, client = self.run_cli(["diagnose", "--report", str(report)])
            self.assertEqual(code, 1)
            self.assertEqual(result["error"]["code"], "report_unavailable")
            self.assertEqual(client.calls, [])
            self.assertEqual(report.read_bytes(), original)

    def test_report_cannot_equal_source_controls_or_output_before_engine_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = str(Path(tmp) / "source.hwpx")
            control = str(Path(tmp) / "control.json")
            output = str(Path(tmp) / "output.hwpx")
            cases = [
                (["parse", source], source),
                (["compare", "before.hwpx", source], source),
                (["fill", source, "--values-file", control], control),
                (["patch", source, "--markdown-file", control], control),
                (["fill", source, "--values-file", control, "--output", output, "--apply"], output),
            ]
            for argv, report in cases:
                with self.subTest(argv=argv):
                    code, result, client = self.run_cli(argv + ["--report", report])
                    self.assertEqual(code, 1)
                    self.assertEqual(result["error"]["code"], "invalid_arguments")
                    self.assertEqual(client.calls, [])
                    self.assertFalse(Path(report).exists())

    def test_no_report_creates_no_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "missing.hwpx"
            self.run_cli(["parse", str(source)])
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_global_flags_before_or_after_command_reach_lazy_client(self):
        for argv in (["--package-dir", "pkg", "--node-path", "node", "--timeout", "9", "diagnose"],
                     ["diagnose", "--package-dir", "pkg", "--node-path", "node", "--timeout", "9"]):
            fake_module = types.ModuleType("kordoc_client")
            captured = []

            def create(**kwargs):
                captured.append(kwargs)
                return FakeClient()

            fake_module.KordocClient = create
            with patch.dict(sys.modules, {"kordoc_client": fake_module}):
                code = document_cli.main(argv, stdout=io.StringIO())
            self.assertEqual(code, 0)
            self.assertEqual(captured, [{"package_dir": "pkg", "node_path": "node", "timeout": 9.0}])

    def test_import_and_help_do_not_import_backend_or_converter(self):
        blocked = {"kordoc_client": None, "anyway_to_hwpx_com": None, "win32com": None, "pythoncom": None}
        with patch.dict(sys.modules, blocked):
            importlib.reload(document_cli)
            stream = io.StringIO()
            self.assertEqual(document_cli.main(["--help"], stdout=stream), 0)
            self.assertIn("--report", stream.getvalue())

    def test_bad_backend_json_is_structured(self):
        for bad_result in (None, {"status": "unknown"}, {"status": "success", "data": object()}):
            client = FakeClient()
            with patch.object(client, "request", return_value=bad_result):
                code, result, _ = self.run_cli(["diagnose"], client)
            self.assertEqual(code, 1)
            self.assertEqual(result["error"]["code"], "invalid_response")


if __name__ == "__main__":
    unittest.main()
