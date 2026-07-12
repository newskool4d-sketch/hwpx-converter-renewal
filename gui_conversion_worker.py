from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

import anyway_to_hwpx_com as converter
import pythoncom
import time
import traceback


Failure: TypeAlias = tuple[str, BaseException]
ConversionMessage: TypeAlias = (
    tuple[str, int, int, str]
    | tuple[str, str, str | None]
    | tuple[str, int, list[Failure]]
)
MessageSink: TypeAlias = Callable[[ConversionMessage], None]


@dataclass(frozen=True, slots=True)
class ConversionSnapshot:
    files: tuple[str, ...]
    output_dir: str
    empty_output_folder: bool
    insert_end_mark: bool
    pdf_mode: str


def run_conversion(snapshot: ConversionSnapshot, message_sink: MessageSink) -> None:
    pythoncom.CoInitialize()
    hwp = None
    failures: list[Failure] = []
    completed = 0
    total = len(snapshot.files)
    try:
        prepared_output_dir = converter.prepare_output_dir(
            snapshot.output_dir,
            empty_output_folder=snapshot.empty_output_folder,
        )
        hwp = converter.create_hwp_object(visible=True)
        time.sleep(1.5)

        for src in snapshot.files:
            try:
                src_path = converter.as_path(src)
                out_path = converter.build_output_path(src_path, prepared_output_dir)
                message_sink(("progress", completed, total, src_path.name))
                message_sink(("log", f"변환 중: {src_path.name} → {out_path.name}", None))
                result = converter.convert_file(
                    hwp,
                    src_path,
                    out_path,
                    insert_end_mark=snapshot.insert_end_mark,
                    kordoc_home=None,
                    pdf_mode=snapshot.pdf_mode,
                )
                converter.record_output_file(prepared_output_dir, out_path)
                completed += 1
                message_sink(("progress", completed, total, src_path.name))
                message_sink(("log", f"완료: {out_path.name}", "ok"))
                for note in (result or {}).get("notes", []):
                    tag = "err" if note.startswith("[확인 필요]") else "muted"
                    message_sink(("log", note, tag))
            except Exception as exc:  # noqa: BLE001,BROAD_EXCEPT_OK
                failures.append((src, exc))
                message_sink(("log", f"실패: {Path(src).name} — {exc}", "err"))
    except Exception as exc:  # noqa: BLE001,BROAD_EXCEPT_OK
        failures.append(("HWP 실행", exc))
        message_sink(("log", traceback.format_exc(), "err"))
    finally:
        if hwp is not None:
            try:
                hwp.Quit()
            except Exception:  # noqa: BLE001,BROAD_EXCEPT_OK
                pass
        pythoncom.CoUninitialize()
        message_sink(("done", completed, failures))
