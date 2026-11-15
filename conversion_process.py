"""Bounded, app-owned conversion processes.

A Hancom process is terminated only when this job started it itself: it did not
exist before the job's COM object was created, and its image name and creation
time still match when the job is stopped. A user's own Hancom window is never touched.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import multiprocessing
import os
from pathlib import Path
import shutil
import time

_child_cancel_event = None
_CANCEL_GRACE_SECONDS = 2.0
_HWP_IMAGE_NAME = "hwp.exe"
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_PROCESS_TERMINATE = 0x0001


def _process_identity(pid, access=_PROCESS_QUERY_LIMITED_INFORMATION):
    """Return (image name, creation time) for a live process, or None."""
    if os.name != "nt" or not isinstance(pid, int) or pid <= 0:
        return None
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel32.OpenProcess(access, False, pid)
    if not handle:
        return None
    try:
        exit_code = wintypes.DWORD()
        kernel32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)) or exit_code.value != 259:
            return None  # 259 = STILL_ACTIVE
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        kernel32.QueryFullProcessImageNameW.argtypes = (
            wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD))
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return None
        times = [wintypes.FILETIME() for _ in range(4)]
        kernel32.GetProcessTimes.argtypes = (wintypes.HANDLE,) + (ctypes.POINTER(wintypes.FILETIME),) * 4
        if not kernel32.GetProcessTimes(handle, *(ctypes.byref(item) for item in times)):
            return None
        created = (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
        return os.path.basename(buffer.value).lower(), created
    finally:
        kernel32.CloseHandle(handle)


def _terminate_owned_hwp(owned):
    """Terminate the Hancom process this job started, if it is still that same process."""
    if not owned:
        return False
    pid, created = owned
    if _process_identity(pid) != (_HWP_IMAGE_NAME, created):
        return False  # already gone, or the PID now belongs to something else
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.TerminateProcess.argtypes = (wintypes.HANDLE, wintypes.UINT)
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel32.OpenProcess(_PROCESS_TERMINATE, False, pid)
    if not handle:
        return False
    try:
        return bool(kernel32.TerminateProcess(handle, 1))
    finally:
        kernel32.CloseHandle(handle)


def _owned_hwp_process(hwp, existing_pids):
    """Identify the Hancom process behind ``hwp`` only if this job created it."""
    try:
        import win32process

        window = hwp.XHwpWindows.Item(0).WindowHandle
        _thread, pid = win32process.GetWindowThreadProcessId(int(window))
    except Exception:  # noqa: BLE001 — identification is best effort; unknown means "do not terminate"
        return None
    identity = _process_identity(pid)
    if pid in existing_pids or identity is None or identity[0] != _HWP_IMAGE_NAME:
        return None
    return pid, identity[1]


def _running_hwp_pids():
    try:
        import win32process

        pids = win32process.EnumProcesses()
    except Exception:  # noqa: BLE001
        return None
    return {pid for pid in pids if (_process_identity(pid) or ("",))[0] == _HWP_IMAGE_NAME}


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
        existing_pids = _running_hwp_pids()
        hwp = _create_private_hwp(
            converter, warn=lambda message: connection.send(("log", str(message)))
        )
        # Without a reliable "before" list we cannot prove ownership, so report nothing.
        owned = _owned_hwp_process(hwp, existing_pids) if existing_pids is not None else None
        if owned:
            connection.send(("hwp_process", owned))
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
    owned_hwp = None
    clean_exit = False
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
                    elif message is not None and message[0] == "hwp_process":
                        owned_hwp = message[1]
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
                # The child reached its own cleanup and asked Hancom to quit.
                clean_exit = result is not None
                return result or ProcessResult("error", error="작업 프로세스가 결과 없이 종료되었습니다.")
            if not pipe_open:
                process.join(timeout=min(0.05, remaining))
    except Exception as exc:  # noqa: BLE001,BROAD_EXCEPT_OK
        return ProcessResult("error", error=f"작업 프로세스 실행 실패: {exc}")
    finally:
        if started:
            _stop_owned_process(process)
            # A stopped or crashed job cannot quit Hancom itself; its private instance would
            # stay behind holding the staged output open.
            if not clean_exit and _terminate_owned_hwp(owned_hwp) and log_sink is not None:
                log_sink("[참고] 중단된 변환이 띄운 한글 프로세스를 정리했습니다. 직접 열어 둔 한글 창에는 영향이 없습니다.")
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
