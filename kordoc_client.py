"""Optional, local-only kordoc adapter. Importing this module needs no Node install.

Every request returns an envelope; callers must inspect ``status`` rather than
mistaking a partially applied edit for success. No document content is logged.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
from typing import Any
import uuid


ACTIONS = frozenset({"diagnose", "parse", "compare", "validate", "fields",
                     "fill", "patch", "render", "profile", "lint"})
MAX_OUTPUT_BYTES = 32 * 1024 * 1024
MAX_REQUEST_BYTES = 1024 * 1024


def _error(action: str, code: str, message: str, *, cancelled: bool = False) -> dict:
    return {"ok": False, "status": "cancelled" if cancelled else "error",
            "action": action, "data": None, "warnings": [],
            "error": {"code": code, "message": message}}


def _package_at(path: Path) -> Path | None:
    for candidate in (path, path / "node_modules" / "kordoc"):
        if (candidate / "package.json").is_file() and (candidate / "dist" / "index.js").is_file():
            return candidate.resolve()
    return None


class KordocClient:
    """Run one bounded Node process per operation; never install on demand.

    Package selection: explicit argument, HWPX_KORDOC_HOME, app-adjacent deps,
    then source-adjacent deps. An invalid explicit location fails closed.
    ``cancel_event`` can be a threading.Event. Cancellation kills only this
    request's Node process; the bridge does not start COM or other children.
    """

    def __init__(self, package_dir=None, node_path=None, timeout=120):
        self.package_dir = package_dir
        self.node_path = node_path
        self.timeout = float(timeout)
        self.bridge_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "kordoc_bridge.mjs"

    def _package(self) -> Path | None:
        explicit = self.package_dir or os.environ.get("HWPX_KORDOC_HOME")
        if explicit:
            return _package_at(Path(explicit).expanduser())
        locations = [Path(sys.executable).resolve().parent / "deps" / "kordoc",
                     Path(__file__).resolve().parent / "deps" / "kordoc"]
        return next((found for location in locations if (found := _package_at(location))), None)

    def _node(self) -> str | None:
        explicit = self.node_path or os.environ.get("HWPX_NODE_PATH")
        if explicit:
            path = Path(explicit).expanduser()
            return str(path.resolve()) if path.is_file() else None
        adjacent = Path(sys.executable).resolve().parent / "deps" / "node" / "node.exe"
        return str(adjacent) if adjacent.is_file() else shutil.which("node")

    def request(self, action: str, *, cancel_event=None, **kwargs: Any) -> dict:
        """Return {ok,status,action,data,warnings,error}; never raise for job errors."""
        if action not in ACTIONS:
            return _error(action, "UNSUPPORTED_ACTION", "지원하지 않는 문서 작업입니다.")
        if cancel_event is not None and cancel_event.is_set():
            return _error(action, "CANCELLED", "작업을 취소했습니다.", cancelled=True)
        try:
            package = self._package()
            node = self._node()
            if not package:
                return _error(action, "PACKAGE_NOT_FOUND", "kordoc 설치 폴더를 찾지 못했습니다. deps/kordoc 또는 HWPX_KORDOC_HOME을 확인하세요.")
            if not node:
                return _error(action, "NODE_NOT_FOUND", "Node.js 실행 파일을 찾지 못했습니다. Node 20 이상 또는 HWPX_NODE_PATH가 필요합니다.")
            if not self.bridge_path.is_file():
                return _error(action, "BRIDGE_NOT_FOUND", "kordoc_bridge.mjs 파일을 찾지 못했습니다.")
            request_id = uuid.uuid4().hex
            payload = json.dumps({"id": request_id, "action": action,
                                  "args": kwargs}, ensure_ascii=False,
                                 default=lambda value: os.fspath(value)).encode("utf-8")
            if len(payload) > MAX_REQUEST_BYTES:
                return _error(action, "INPUT_TOO_LARGE", "요청 크기 제한(1 MiB)을 초과했습니다.")
            # Ignore user Node preload hooks; preserve normal native library paths.
            env = os.environ.copy()
            env.pop("NODE_OPTIONS", None)
            env.pop("NODE_PATH", None)
            env.update({"KORDOC_OFFLINE": "1", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
                        "HF_HUB_DISABLE_TELEMETRY": "1"})
            with subprocess.Popen(
                [node, "--max-old-space-size=512", str(self.bridge_path), str(package)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                shell=False, env=env,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            ) as process:
                return self._exchange(process, payload, action, request_id, cancel_event)
        except (OSError, ValueError, TypeError, subprocess.SubprocessError):
            return _error(action, "CLIENT_ERROR", "문서 작업 프로세스를 실행하지 못했습니다. 경로와 실행 권한을 확인하세요.")

    def _exchange(self, process, payload, action, request_id, cancel_event):
        output = bytearray()
        oversized = threading.Event()

        def read(stream, collect):
            total = 0
            try:
                while chunk := stream.read(65536):
                    total += len(chunk)
                    if total > MAX_OUTPUT_BYTES:
                        oversized.set()
                        break
                    if collect:
                        output.extend(chunk)
            finally:
                stream.close()

        def write():
            try:
                process.stdin.write(payload)
                process.stdin.close()
            except (BrokenPipeError, OSError, ValueError):
                pass

        threads = [threading.Thread(target=read, args=(process.stdout, True), daemon=True),
                   threading.Thread(target=read, args=(process.stderr, False), daemon=True),
                   threading.Thread(target=write, daemon=True)]
        for thread in threads:
            thread.start()
        deadline = time.monotonic() + max(0.01, self.timeout)
        failure = None
        while process.poll() is None:
            if cancel_event is not None and cancel_event.is_set():
                failure = _error(action, "CANCELLED", "작업을 취소했습니다.", cancelled=True)
            elif oversized.is_set():
                failure = _error(action, "OUTPUT_TOO_LARGE", "결과 크기 제한(32 MiB)을 초과했습니다.")
            elif time.monotonic() >= deadline:
                failure = _error(action, "TIMEOUT", "문서 작업 제한 시간을 초과했습니다.")
            if failure:
                process.kill()
                break
            time.sleep(0.03)
        process.wait(timeout=5)
        for thread in threads:
            thread.join(timeout=2)
        if failure:
            return failure
        if oversized.is_set():
            return _error(action, "OUTPUT_TOO_LARGE", "결과 크기 제한(32 MiB)을 초과했습니다.")
        if process.returncode:
            return _error(action, "PROCESS_FAILED", "kordoc 작업 프로세스가 비정상 종료했습니다.")
        try:
            result = json.loads(output.decode("utf-8"))
            if (not isinstance(result, dict) or result.get("id") != request_id
                    or result.get("action") != action
                    or result.get("status") not in {"success", "partial", "error", "cancelled"}
                    or not isinstance(result.get("warnings"), list)
                    or result.get("ok") is not (result["status"] == "success")
                    or "data" not in result or "error" not in result):
                raise ValueError("Invalid bridge envelope")
            return result
        except (UnicodeDecodeError, ValueError, KeyError):
            return _error(action, "INVALID_RESPONSE", "kordoc 응답 형식이 올바르지 않습니다.")
