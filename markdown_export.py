"""HWP·HWPX·PDF → Markdown export through the local kordoc bridge (no Hancom COM).

The bridge writes into a private staging folder inside the output folder. This
module chooses free final names, publishes the image folder and the Markdown file
without replacing anything, and always removes the staging folder, so a cancelled
or timed-out run leaves nothing partial behind.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import tempfile

MARKDOWN_INPUT_EXTENSIONS = frozenset({".hwp", ".hwpx", ".hwpml", ".hml", ".pdf"})
STAGING_PREFIX = ".to-md-"
DEFAULT_TIMEOUT_SECONDS = 300


def _error(code: str, message: str, *, status: str = "error") -> dict:
    return {"ok": False, "status": status, "action": "to_markdown", "data": None,
            "warnings": [], "error": {"code": code, "message": message}}


def output_names(source: Path, output_dir: Path) -> tuple[Path, str]:
    """Return a free ``<stem>.md`` path and its matching ``<stem>_images`` folder name."""
    for index in range(1, 1000):
        stem = source.stem if index == 1 else f"{source.stem} - {index}"
        markdown = output_dir / f"{stem}.md"
        image_dir = f"{stem}_images"
        if not markdown.exists() and not (output_dir / image_dir).exists():
            return markdown, image_dir
    raise FileExistsError(f"저장 가능한 파일명을 찾지 못했습니다: {output_dir / (source.stem + '.md')}")


def convert_to_markdown(source, output_dir=None, *, images: bool = True, client=None, cancel_event=None) -> dict:
    """Convert one document; returns the bridge envelope with final paths in ``data``."""
    source = Path(source).expanduser().resolve()
    if source.suffix.lower() not in MARKDOWN_INPUT_EXTENSIONS:
        return _error("UNSUPPORTED_FORMAT", "한글(HWP·HWPX·HWPML)과 PDF 문서만 Markdown으로 변환합니다.")
    if not source.is_file():
        return _error("INVALID_PATH", f"입력 파일을 찾을 수 없습니다: {source.name}")
    output_dir = Path(output_dir).expanduser().resolve() if output_dir else source.parent
    if client is None:
        from kordoc_client import KordocClient

        client = KordocClient(timeout=DEFAULT_TIMEOUT_SECONDS)
    staging = None
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        markdown_path, image_dir = output_names(source, output_dir)
        staging = Path(tempfile.mkdtemp(prefix=STAGING_PREFIX, dir=output_dir))
        result = client.request("to_markdown", cancel_event=cancel_event, path=str(source),
                                staging_dir=str(staging), image_dir_name=image_dir, images=images)
        if result.get("status") not in ("success", "partial"):
            return result
        if cancel_event is not None and cancel_event.is_set():
            return _error("CANCELLED", "작업을 취소했습니다.", status="cancelled")
        data = result.get("data") or {}
        published = []
        try:
            if data.get("imageDir"):
                # os.rename refuses an existing destination on Windows; checked again for POSIX.
                if (output_dir / image_dir).exists():
                    raise FileExistsError(f"같은 이름의 폴더가 생겼습니다: {image_dir}")
                os.rename(staging / image_dir, output_dir / image_dir)
                published.append(output_dir / image_dir)
            with (staging / "document.md").open("rb") as staged, markdown_path.open("xb") as target:
                published.append(markdown_path)
                shutil.copyfileobj(staged, target)
        except Exception:
            for path in reversed(published):
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    path.unlink(missing_ok=True)
            raise
        # Deliberately not recorded in the HWPX output manifest: exported Markdown is meant
        # to be edited, so "저장 폴더 비우기" must stop at these files rather than delete them.
        data = dict(data, output=str(markdown_path),
                    imageDir=str(output_dir / image_dir) if data.get("imageDir") else None)
        return dict(result, data=data)
    except (OSError, ValueError) as exc:
        return _error("SAVE_FAILED", f"Markdown 파일을 저장하지 못했습니다: {exc}")
    finally:
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)
