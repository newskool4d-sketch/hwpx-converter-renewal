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
    | tuple[str, int, list[Failure], list[str]]
    | tuple[str]
)
MessageSink: TypeAlias = Callable[[ConversionMessage], None]
_WARNING_PREFIXES = ("[경고]", "[확인 필요]")


def note_log_tag(note: str) -> str:
    if note.startswith("[확인 필요]"):
        return "err"
    if note.startswith("[경고]"):
        return "warn"
    if note.startswith("[표기 점검]"):
        return "info"
    return "muted"


@dataclass(frozen=True, slots=True)
class ConversionSnapshot:
    files: tuple[str, ...]
    output_dir: str
    empty_output_folder: bool
    insert_end_mark: bool
    pdf_mode: str
    official: bool = False
    doc_type: str = "plan"
    file_timeout_seconds: float = 180


def run_conversion(
    snapshot: ConversionSnapshot,
    message_sink: MessageSink,
    *,
    isolate: bool = False,
    cancel_event=None,
) -> None:
    if isolate:
        _run_isolated_conversion(snapshot, message_sink, cancel_event=cancel_event)
        return
    pythoncom.CoInitialize()
    hwp = None
    failures: list[Failure] = []
    warned: list[str] = []
    completed = 0
    total = len(snapshot.files)
    try:
        prepared_output_dir = converter.prepare_output_dir(
            snapshot.output_dir,
            empty_output_folder=snapshot.empty_output_folder,
        )
        hwp = converter.create_hwp_object(
            visible=True, warn=lambda message: message_sink(("log", message, note_log_tag(message)))
        )
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
                    official=snapshot.official,
                    doc_type=snapshot.doc_type,
                )
                converter.record_output_file(prepared_output_dir, out_path)
                completed += 1
                message_sink(("progress", completed, total, src_path.name))
                message_sink(("log", f"완료: {out_path.name}", "ok"))
                notes = (result or {}).get("notes", [])
                for note in notes:
                    message_sink(("log", note, note_log_tag(note)))
                if any(note.startswith(_WARNING_PREFIXES) for note in notes):
                    warned.append(src_path.name)
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
        message_sink(("done", completed, failures, warned))


def _run_isolated_conversion(snapshot, message_sink, *, cancel_event=None):
    """Keep one unresponsive COM call from blocking the GUI or the next file."""
    import math
    import shutil
    import tempfile

    from conversion_process import publish_output, run_file_process

    failures: list[Failure] = []
    warned: list[str] = []
    completed = 0
    processed = 0
    total = len(snapshot.files)
    cancelled = False
    try:
        timeout = float(snapshot.file_timeout_seconds)
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("파일별 제한 시간은 0보다 큰 유한한 수여야 합니다.")
        output_root = converter.as_path(snapshot.output_dir)
        # Clearing managed outputs must never remove an input selected for this run.
        if snapshot.empty_output_folder and any(
            converter.as_path(src).is_relative_to(output_root) for src in snapshot.files
        ):
            raise ValueError("입력 파일이 있는 출력 폴더는 비울 수 없습니다.")
        if cancel_event is not None and cancel_event.is_set():
            cancelled = True
        else:
            prepared_output_dir = converter.prepare_output_dir(
                snapshot.output_dir, empty_output_folder=snapshot.empty_output_folder
            )
        for index, src in enumerate(snapshot.files):
            if cancelled or (cancel_event is not None and cancel_event.is_set()):
                cancelled = True
                failures.extend((pending, RuntimeError("취소되어 처리하지 않음")) for pending in snapshot.files[index:])
                break
            staging_dir = None
            try:
                src_path = converter.as_path(src)
                out_path = converter.build_output_path(src_path, prepared_output_dir)
                if src_path == out_path.resolve():
                    raise ValueError("원본 파일과 출력 경로가 같습니다.")
                message_sink(("progress", processed, total, src_path.name))
                message_sink(("log", f"변환 중: {src_path.name} → {out_path.name}", None))
                staging_dir = Path(tempfile.mkdtemp(prefix=".conversion-", dir=prepared_output_dir))
                staged_output = staging_dir / out_path.name
                result = run_file_process(
                    src_path,
                    staged_output,
                    options={
                        "insert_end_mark": snapshot.insert_end_mark,
                        "pdf_mode": snapshot.pdf_mode,
                        "official": snapshot.official,
                        "doc_type": snapshot.doc_type,
                    },
                    timeout_seconds=timeout,
                    cancel_event=cancel_event,
                    log_sink=lambda text: message_sink(("log", text, note_log_tag(text))),
                )
                if result.status in ("timeout", "cancelled"):
                    message_sink(("log", "[경고] 작업 프로세스를 중단했습니다. 응답 없는 한글 창이 남아 있으면 직접 확인해 주세요. 사용자의 한글 프로세스는 강제 종료하지 않습니다.", "warn"))
                if result.status == "cancelled":
                    cancelled = True
                    raise RuntimeError("사용자 요청으로 변환 취소")
                if result.status == "timeout":
                    raise TimeoutError(f"파일별 제한 시간 {timeout:g}초 초과")
                if result.status != "ok":
                    raise RuntimeError(result.error or "작업 프로세스 변환 실패")
                if cancel_event is not None and cancel_event.is_set():
                    cancelled = True
                    raise RuntimeError("사용자 요청으로 결과 저장 취소")
                publish_output(staged_output, out_path)
                converter.record_output_file(prepared_output_dir, out_path)
                completed += 1
                message_sink(("log", f"완료: {out_path.name}", "ok"))
                for note in result.notes:
                    message_sink(("log", note, note_log_tag(note)))
                if any(note.startswith(_WARNING_PREFIXES) for note in result.notes):
                    warned.append(src_path.name)
            except Exception as exc:  # noqa: BLE001,BROAD_EXCEPT_OK
                failures.append((src, exc))
                message_sink(("log", f"실패: {Path(src).name} — {exc}", "err"))
            finally:
                processed += 1
                message_sink(("progress", processed, total, Path(src).name))
                if staging_dir is not None:
                    try:
                        shutil.rmtree(staging_dir)
                    except OSError:
                        message_sink(("log", f"[경고] 미완료 임시 파일을 정리하지 못했습니다: {staging_dir.name}", "warn"))
                        if Path(src).name not in warned:
                            warned.append(Path(src).name)
    except Exception as exc:  # noqa: BLE001,BROAD_EXCEPT_OK
        # Preserve real input paths so preparation failures remain retryable.
        already_failed = {src for src, _ in failures}
        failures.extend((src, exc) for src in snapshot.files if src not in already_failed)
        message_sink(("log", f"변환 준비 실패: {exc}", "err"))
    finally:
        if cancelled:
            message_sink(("cancelled",))
        message_sink(("done", completed, failures, warned))
