from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import time
import unittest
from unittest.mock import Mock, patch

import conversion_process as process_worker
from conversion_process import ProcessResult, publish_output, run_file_process
import gui_conversion_worker as worker


def _successful_process(connection, source, destination, options):
    Path(destination).write_bytes(Path(source).read_bytes() + b" converted")
    connection.send(("log", "[경고] test warning"))
    connection.send(("result", ProcessResult("ok", ("[표기 점검] test",))))
    connection.close()


def _hanging_process(connection, source, destination, options):
    Path(destination).write_bytes(b"partial")
    time.sleep(30)


def _crashing_process(connection, source, destination, options):
    os._exit(7)


def _no_result_process(connection, source, destination, options):
    connection.close()


def _result_then_hang_process(connection, source, destination, options):
    connection.send(("result", ProcessResult("ok")))
    time.sleep(30)


def _cooperative_process(connection, source, destination, options):
    # A custom four-argument target sees the same signal as the native worker.
    connection.send(("log", "COOPERATIVE_READY"))
    if process_worker._child_cancel_event.wait(10):
        Path(destination).write_text("cleanup completed", encoding="utf-8")
        connection.send(("log", "COOPERATIVE_CLEANED"))
        # Parent cancellation must take priority even if the child reports ok.
        connection.send(("result", ProcessResult("ok")))
    connection.close()


class ConversionProcessTests(unittest.TestCase):
    def test_native_precancel_does_not_create_a_com_object(self):
        import pythoncom

        event = threading.Event()
        event.set()
        connection = Mock()
        with patch.object(process_worker, "_child_cancel_event", event), patch.object(
            process_worker, "_create_private_hwp"
        ) as create, patch.object(pythoncom, "CoInitialize") as initialize:
            process_worker._convert_in_process(connection, "unused", "unused", {})
        create.assert_not_called()
        initialize.assert_not_called()
        connection.send.assert_called_once_with(("result", ProcessResult("cancelled")))

    def test_native_cancel_after_com_creation_calls_quit_before_result(self):
        import pythoncom

        event = threading.Event()
        hwp = Mock()
        connection = Mock()
        order = []
        hwp.Quit.side_effect = lambda: order.append("quit")
        connection.send.side_effect = lambda value: order.append(value[1].status)

        def create(*args, **kwargs):
            event.set()
            return hwp

        with patch.object(process_worker, "_child_cancel_event", event), patch.object(
            process_worker, "_create_private_hwp", side_effect=create
        ), patch.object(pythoncom, "CoInitialize"), patch.object(pythoncom, "CoUninitialize"), patch.object(
            worker.converter, "convert_file"
        ) as convert:
            process_worker._convert_in_process(connection, "unused", "unused", {})
        convert.assert_not_called()
        hwp.Quit.assert_called_once_with()
        self.assertEqual(order, ["quit", "cancelled"])

    def test_native_startup_wait_is_interruptible_and_closes_com(self):
        import pythoncom

        event = Mock()
        event.is_set.return_value = False
        event.wait.return_value = True
        hwp, connection = Mock(), Mock()
        with patch.object(process_worker, "_child_cancel_event", event), patch.object(
            process_worker, "_create_private_hwp", return_value=hwp
        ), patch.object(pythoncom, "CoInitialize"), patch.object(pythoncom, "CoUninitialize"), patch.object(
            worker.converter, "convert_file"
        ) as convert:
            process_worker._convert_in_process(connection, "unused", "unused", {})
        event.wait.assert_called_once_with(1.5)
        convert.assert_not_called()
        hwp.Quit.assert_called_once_with()
        connection.send.assert_called_once_with(("result", ProcessResult("cancelled")))

    def test_cooperative_cancel_allows_custom_target_cleanup(self):
        with TemporaryDirectory() as temporary:
            cleaned = Path(temporary) / "cleaned.txt"
            cancel = threading.Event()
            logs = []

            def on_log(text):
                logs.append(text)
                if text == "COOPERATIVE_READY":
                    cancel.set()

            result = run_file_process(
                "unused", cleaned, options={}, timeout_seconds=10,
                cancel_event=cancel, log_sink=on_log, _target=_cooperative_process,
            )
            self.assertEqual(result.status, "cancelled")
            self.assertEqual(cleaned.read_text(encoding="utf-8"), "cleanup completed")
            self.assertEqual(logs, ["COOPERATIVE_READY", "COOPERATIVE_CLEANED"])

    def test_cooperative_timeout_remains_timeout_after_child_cleanup(self):
        with TemporaryDirectory() as temporary:
            cleaned = Path(temporary) / "cleaned.txt"
            result = run_file_process(
                "unused", cleaned, options={}, timeout_seconds=2,
                _target=_cooperative_process,
            )
            self.assertEqual(result.status, "timeout")
            self.assertEqual(cleaned.read_text(encoding="utf-8"), "cleanup completed")

    def test_private_com_creation_does_not_use_running_object_dispatch(self):
        import win32com.client

        hwp = Mock()
        converter = Mock()
        converter.register_security_module.return_value = "FilePathCheckerModule"
        with patch.object(win32com.client, "DispatchEx", return_value=hwp) as dispatch_ex, patch.object(
            win32com.client, "Dispatch"
        ) as dispatch:
            self.assertIs(process_worker._create_private_hwp(converter, Mock()), hwp)
        dispatch_ex.assert_called_once_with("HWPFrame.HwpObject")
        dispatch.assert_not_called()
        converter.register_security_module.assert_called_once_with(hwp)
        hwp.Quit.assert_not_called()

    def test_private_com_setup_failure_closes_only_created_object(self):
        import win32com.client

        hwp = Mock()
        hwp.XHwpWindows.Item.side_effect = RuntimeError("window setup failed")
        converter = Mock()
        with patch.object(win32com.client, "DispatchEx", return_value=hwp):
            with self.assertRaisesRegex(RuntimeError, "window setup"):
                process_worker._create_private_hwp(converter, Mock())
        hwp.Quit.assert_called_once_with()

    def test_spawn_returns_output_and_notes_without_modifying_source(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, destination = root / "원본.md", root / "결과.hwpx"
            source.write_bytes(b"source")
            logs = []
            result = run_file_process(
                source, destination, options={}, timeout_seconds=10,
                log_sink=logs.append, _target=_successful_process,
            )
            self.assertEqual(result.status, "ok", result)
            self.assertEqual(result.notes, ("[표기 점검] test",))
            self.assertEqual(logs, ["[경고] test warning"])
            self.assertEqual(source.read_bytes(), b"source")
            self.assertEqual(destination.read_bytes(), b"source converted")

    def test_hung_spawn_times_out_and_does_not_leave_our_process_running(self):
        import multiprocessing

        with TemporaryDirectory() as temporary:
            destination = Path(temporary) / "partial.hwpx"
            result = run_file_process(
                "unused", destination, options={}, timeout_seconds=0.5,
                _target=_hanging_process,
            )
            self.assertEqual(result.status, "timeout")
            self.assertFalse(any(p.name == "HWPX file conversion" for p in multiprocessing.active_children()))

    def test_running_spawn_can_be_cancelled(self):
        with TemporaryDirectory() as temporary:
            cancel = threading.Event()
            timer = threading.Timer(0.5, cancel.set)
            timer.start()
            try:
                result = run_file_process(
                    "unused", Path(temporary) / "partial.hwpx", options={}, timeout_seconds=10,
                    cancel_event=cancel, _target=_hanging_process,
                )
            finally:
                timer.join()
            self.assertEqual(result.status, "cancelled")

    def test_crashed_spawn_reports_exit_code(self):
        result = run_file_process(
            "unused", "unused", options={}, timeout_seconds=10, _target=_crashing_process,
        )
        self.assertEqual(result.status, "error")
        self.assertIn("7", result.error)

    def test_spawn_without_result_reports_failure(self):
        result = run_file_process(
            "unused", "unused", options={}, timeout_seconds=10, _target=_no_result_process,
        )
        self.assertEqual(result.status, "error")
        self.assertIn("결과 없이", result.error)

    def test_success_message_does_not_hide_process_shutdown_hang(self):
        result = run_file_process(
            "unused", "unused", options={}, timeout_seconds=1.5, _target=_result_then_hang_process,
        )
        self.assertEqual(result.status, "timeout")

    def test_publish_preserves_existing_target_and_rejects_empty_output(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            staged, target = root / "staged.hwpx", root / "source.hwpx"
            staged.write_bytes(b"new")
            target.write_bytes(b"original")
            with self.assertRaises(FileExistsError):
                publish_output(staged, target)
            self.assertEqual(target.read_bytes(), b"original")
            staged.write_bytes(b"")
            with self.assertRaisesRegex(RuntimeError, "비어"):
                publish_output(staged, root / "empty.hwpx")
            self.assertFalse((root / "empty.hwpx").exists())


class IsolatedBatchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.output = self.root / "output"
        self.files = tuple(str(self.root / name) for name in ("a.md", "b.md", "c.md"))
        for name in self.files:
            Path(name).write_text("original", encoding="utf-8")
        self.snapshot = worker.ConversionSnapshot(
            self.files, str(self.output), False, True, "layout", True, "sihaengmun", 2,
        )

    def assert_sources_preserved(self):
        for src in self.files:
            self.assertEqual(Path(src).read_text(encoding="utf-8"), "original")

    def test_timeout_then_success_continues_and_progress_counts_attempts(self):
        calls = []

        def fake_run(src, staged, **kwargs):
            calls.append((src, kwargs))
            staged.write_bytes(b"partial" if src.name == "a.md" else b"complete")
            if src.name == "a.md":
                return ProcessResult("timeout")
            return ProcessResult("ok", ("[표기 점검] note",))

        messages = []
        with patch.object(process_worker, "run_file_process", side_effect=fake_run), patch.object(
            worker.converter, "prepare_output_dir", wraps=worker.converter.prepare_output_dir,
        ) as prepare:
            worker.run_conversion(self.snapshot, messages.append, isolate=True)
        self.assertEqual(prepare.call_count, 1)
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[0][1]["options"], {
            "insert_end_mark": True, "pdf_mode": "layout", "official": True, "doc_type": "sihaengmun",
        })
        self.assertEqual(calls[0][1]["timeout_seconds"], 2)
        done = messages[-1]
        self.assertEqual(done[0:2], ("done", 2))
        self.assertEqual([src for src, _ in done[2]], [self.files[0]])
        self.assertIsInstance(done[2][0][1], TimeoutError)
        self.assertEqual(done[3], [])
        self.assertIn(("progress", 3, 3, "c.md"), messages)
        self.assertFalse((self.output / "a.hwpx").exists())
        self.assertEqual((self.output / "b.hwpx").read_bytes(), b"complete")
        self.assertEqual(sorted(p.name for p in self.output.iterdir()), ["b.hwpx", "c.hwpx"])
        self.assert_sources_preserved()

    def test_cancel_marks_current_and_pending_as_retryable(self):
        messages = []
        with patch.object(process_worker, "run_file_process", return_value=ProcessResult("cancelled")) as run:
            worker.run_conversion(self.snapshot, messages.append, isolate=True)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(messages[-2], ("cancelled",))
        self.assertEqual(messages[-1][1], 0)
        self.assertEqual([src for src, _ in messages[-1][2]], list(self.files))
        self.assert_sources_preserved()

    def test_cancel_after_worker_return_does_not_publish(self):
        cancel = threading.Event()

        def fake_run(src, staged, **kwargs):
            staged.write_bytes(b"converted")
            cancel.set()
            return ProcessResult("ok")

        messages = []
        with patch.object(process_worker, "run_file_process", side_effect=fake_run):
            worker.run_conversion(self.snapshot, messages.append, isolate=True, cancel_event=cancel)
        self.assertEqual(messages[-2], ("cancelled",))
        self.assertEqual(len(messages[-1][2]), 3)
        self.assertEqual(messages[-1][1], 0)
        self.assertEqual(list(self.output.iterdir()), [])
        self.assert_sources_preserved()

    def test_pre_cancel_does_not_prepare_or_empty_output(self):
        cancel = threading.Event()
        cancel.set()
        messages = []
        with patch.object(worker.converter, "prepare_output_dir") as prepare:
            worker.run_conversion(self.snapshot, messages.append, isolate=True, cancel_event=cancel)
        prepare.assert_not_called()
        self.assertEqual(len(messages[-1][2]), 3)
        self.assertEqual(messages[-2], ("cancelled",))

    def test_input_within_output_is_not_deleted_by_empty_option(self):
        messages = []
        snapshot = replace(self.snapshot, output_dir=str(self.root), empty_output_folder=True)
        with patch.object(worker.converter, "prepare_output_dir") as prepare:
            worker.run_conversion(snapshot, messages.append, isolate=True)
        prepare.assert_not_called()
        self.assertEqual(len(messages[-1][2]), 3)
        self.assert_sources_preserved()

    def test_name_collision_preserves_existing_document(self):
        self.output.mkdir()
        (self.output / "a.hwpx").write_bytes(b"existing")

        def fake_run(src, staged, **kwargs):
            staged.write_bytes(b"converted")
            return ProcessResult("ok")

        messages = []
        with patch.object(process_worker, "run_file_process", side_effect=fake_run):
            worker.run_conversion(replace(self.snapshot, files=self.files[:1]), messages.append, isolate=True)
        self.assertEqual(messages[-1], ("done", 1, [], []))
        self.assertEqual((self.output / "a.hwpx").read_bytes(), b"existing")
        self.assertEqual((self.output / "a - 2.hwpx").read_bytes(), b"converted")
        self.assert_sources_preserved()

    def test_failed_process_partial_output_is_never_published(self):
        def fake_run(src, staged, **kwargs):
            staged.write_bytes(b"partial")
            return ProcessResult("error", error="conversion failed")

        messages = []
        with patch.object(process_worker, "run_file_process", side_effect=fake_run):
            worker.run_conversion(self.snapshot, messages.append, isolate=True)
        self.assertEqual(messages[-1][1], 0)
        self.assertEqual(len(messages[-1][2]), 3)
        self.assertEqual(list(self.output.iterdir()), [])
        self.assert_sources_preserved()


if __name__ == "__main__":
    unittest.main()
