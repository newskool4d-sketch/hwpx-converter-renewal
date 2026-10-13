"""Bounded, app-owned conversion processes; never terminate a Hancom process."""
from __future__ import annotations

from dataclasses import dataclass
import multiprocessing
from pathlib import Path
import shutil
import time

_child_cancel_event = None
_CANCEL_GRACE_SECONDS = 2.0


class _ConversionCancelled(Exception):
    pass


def _check_child_cancelled():
    if _child_cancel_event is not None and _child_cancel_event.is_set():
        raise _ConversionCancelled


def _wait_before_conversion(seconds):
    if _child_cancel_event is None:
        time.sleep(seconds)
    elif _child_cancel_event.wait(seconds):
        raise _ConversionCancelled


def _run_target_with_cancel(target, connection, source, destination, options, cancel_event):
    """Retain the four-argument target contract, including native probe wrappers."""
    global _child_cancel_event
    previous = _child_cancel_event
    _child_cancel_event = cancel_event
    try:
        target(connection, source, destination, options)
    finally:
        _child_cancel_event = previous


@dataclass(frozen=True, slots=True)
class ProcessResult:
    status: str
    notes: tuple[str, ...] = ()
    error: str = ""


def _create_private_hwp(converter, warn):
    import win32com.client

    hwp = win32com.client.DispatchEx("HWPFrame.HwpObject")
    try:
        if converter.register_security_module(hwp) is None:
            warn(converter._SECURITY_MODULE_WARNING)
        hwp.XHwpWindows.Item(0).Visible = True
        return hwp
    except Exception:
        # This handle came from DispatchEx, never the user's active COM object.
        try:
            hwp.Quit()
        except Exception:
            pass
        raise


def _convert_in_process(connection, source, destination, options):
    """Only this spawned process owns the COM apartment and conversion object."""
    import anyway_to_hwpx_com as converter
    import pythoncom

    hwp = None
    initialized = False
    result = ProcessResult("error", error="변환 작업이 완료되지 않았습니다.")
    try:
        _check_child_cancelled()
        pythoncom.CoInitialize()
        initialized = True
        hwp = _create_private_hwp(
            converter, warn=lambda message: connection.send(("log", str(message)))
        )
        _check_child_cancelled()
        _wait_before_conversion(1.5)
        _check_child_cancelled()
        converted = converter.convert_file(
            hwp, Path(source), Path(destination), kordoc_home=None, **options
        )
        _check_child_cancelled()
        result = ProcessResult("ok", tuple(str(note) for note in (converted or {}).get("notes", [])))
    except _ConversionCancelled:
        result = ProcessResult("cancelled")
    except Exception as exc:  # noqa: BLE001,BROAD_EXCEPT_OK
        result = ProcessResult("error", error=f"{type(exc).__name__}: {exc}")
    finally:
        if hwp is not None:
            try:
                hwp.Quit()
            except Exception:  # noqa: BLE001,BROAD_EXCEPT_OK
                result = ProcessResult(
                    result.status,
                    result.notes + ("[경고] 한글 창을 정상 종료하지 못했습니다. 남아 있는 창을 확인해 주세요.",),
                    result.error,
                )
        if initialized:
            pythoncom.CoUninitialize()
        try:
            connection.send(("result", result))
        finally:
            connection.close()


def _stop_owned_process(process):
    """Terminate exactly the process object created by this call, without a tree kill."""
    if process.is_alive():
        process.terminate()
        process.join(timeout=1)
    if process.is_alive():
        process.kill()
        process.join(timeout=1)


def run_file_process(
    source,
    destination,
    *,
    options,
    timeout_seconds,
    cancel_event=None,
    log_sink=None,
    _target=None,
):
    """Return after success, crash, timeout or cancellation, including COM shutdown."""
    context = multiprocessing.get_context("spawn")
    receiving, sending = context.Pipe(duplex=False)
    child_cancel = context.Event()
    process = context.Process(
        target=_run_target_with_cancel,
        args=(_target or _convert_in_process, sending, str(source), str(destination), options, child_cancel),
        name="HWPX file conversion",
    )
    started = False
    result = None
    stop_status = None
    shutdown_deadline = None
    deadline = time.monotonic() + timeout_seconds
    try:
        if cancel_event is not None and cancel_event.is_set():
            return ProcessResult("cancelled")
        process.start()
        started = True
        sending.close()
        pipe_open = True
        while True:
            now = time.monotonic()
            if stop_status is None:
                if cancel_event is not None and cancel_event.is_set():
                    stop_status = "cancelled"
                elif now >= deadline:
                    stop_status = "timeout"
                if stop_status is not None:
                    child_cancel.set()
                    shutdown_deadline = now + _CANCEL_GRACE_SECONDS
            remaining = (shutdown_deadline if stop_status is not None else deadline) - now
            if remaining <= 0:
                return ProcessResult(stop_status or "timeout")
            if pipe_open:
                try:
                    message = receiving.recv() if receiving.poll(min(0.05, remaining)) else None
                except (EOFError, OSError):
                    # Windows can signal a closed named pipe as WinError 109.
                    pipe_open = False
                else:
                    if message is not None and message[0] == "log" and log_sink is not None:
                        log_sink(message[1])
                    elif message is not None and message[0] == "result":
                        result = message[1]
            # Drain any final messages before inspecting a completed process.
            pending = False
            alive = process.is_alive()
            if not alive and pipe_open:
                try:
                    pending = receiving.poll()
                except (EOFError, OSError):
                    pipe_open = False
            if not alive and not pending:
                process.join(timeout=0)
                if stop_status is not None:
                    return ProcessResult(stop_status, result.notes if result else ())
                if process.exitcode != 0:
                    return ProcessResult("error", error=f"작업 프로세스가 비정상 종료되었습니다 (코드 {process.exitcode}).")
                return result or ProcessResult("error", error="작업 프로세스가 결과 없이 종료되었습니다.")
            if not pipe_open:
                process.join(timeout=min(0.05, remaining))
    except Exception as exc:  # noqa: BLE001,BROAD_EXCEPT_OK
        return ProcessResult("error", error=f"작업 프로세스 실행 실패: {exc}")
    finally:
        if started:
            _stop_owned_process(process)
        receiving.close()
        sending.close()
        if not started or not process.is_alive():
            process.close()


def publish_output(staged_output, destination):
    """Publish only a complete, nonempty result, never replace an existing file."""
    staged = Path(staged_output)
    destination = Path(destination)
    if not staged.is_file() or staged.stat().st_size == 0:
        raise RuntimeError("변환 결과 파일이 없거나 비어 있습니다.")
    # Exclusive creation also protects against another run choosing the same name.
    created = False
    try:
        with staged.open("rb") as source, destination.open("xb") as output:
            created = True
            shutil.copyfileobj(source, output)
    except Exception:
        if created:
            destination.unlink(missing_ok=True)
        raise
