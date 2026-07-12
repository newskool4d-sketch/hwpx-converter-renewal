from __future__ import annotations

from pathlib import Path
import queue
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import anyway_to_hwpx_gui as gui
import gui_conversion_worker as worker


GUI_SOURCE = Path(__file__).parents[1] / "anyway_to_hwpx_gui.py"


class GuiCharacterizationTests(unittest.TestCase):
    def test_picker_clear_and_conversion_entry_points_exist(self) -> None:
        source = GUI_SOURCE.read_text(encoding="utf-8")
        self.assertIn("def select_files(self):", source)
        self.assertIn("def clear_files(self):", source)
        self.assertIn("def start_conversion(self):", source)
        self.assertIn("if self.worker and self.worker.is_alive():", source)

    def test_import_fallback_does_not_require_tkinterdnd2(self) -> None:
        source = GUI_SOURCE.read_text(encoding="utf-8")
        self.assertIn("BaseTk", source)
        self.assertIn("tk.Tk", source)

    def test_conversion_snapshot_forwards_editable_mode_without_mutating_layout(self) -> None:
        class Value:
            def __init__(self, value):
                self.value = value

            def get(self):
                return self.value

            def set(self, value):
                self.value = value

        class Progress:
            def configure(self, **kwargs):
                self.config = kwargs

        class Thread:
            def __init__(self, *, target, args, daemon):
                self.target = target
                self.args = args
                self.daemon = daemon

            def start(self):
                started.append(self.args)

        started = []
        app = gui.ConverterApp.__new__(gui.ConverterApp)
        app.files = ["source.pdf"]
        app.output_dir = Value("output")
        app.empty_output_folder = Value(False)
        app.insert_end_mark = Value(True)
        app.pdf_mode = Value("editable")
        app.worker = None
        app.progress = Progress()
        app.status = Value("")
        app._is_busy = lambda: False
        app._set_busy = lambda busy: setattr(app, "busy_snapshot", busy)
        app._append_log = lambda *_args: None

        with patch.object(gui.threading, "Thread", Thread):
            app.start_conversion()

        self.assertEqual(started, [(tuple(["source.pdf"]), "output", False, True, "editable")])
        app.pdf_mode.value = "layout"
        self.assertEqual(started[0][-1], "editable")

    def test_conversion_snapshot_worker_emits_equivalent_messages_after_gui_state_changes(self) -> None:
        class Value:
            def __init__(self, value):
                self.value = value

            def get(self):
                return self.value

            def set(self, value):
                self.value = value

        class Progress:
            def configure(self, **kwargs):
                self.config = kwargs

        class Thread:
            def __init__(self, *, target, args, daemon):
                self.target = target
                self.args = args
                self.daemon = daemon

            def start(self):
                started.append(self)

            def is_alive(self):
                return False

        class Hwp:
            def Quit(self):
                quit_calls.append(True)

        started = []
        quit_calls = []
        app = gui.ConverterApp.__new__(gui.ConverterApp)
        app.files = []
        app.output_dir = Value("")
        app.empty_output_folder = Value(False)
        app.insert_end_mark = Value(False)
        app.pdf_mode = Value("layout")
        app.worker = None
        app.progress = Progress()
        app.status = Value("")
        app.messages = queue.Queue()
        app._is_busy = lambda: False
        app._set_busy = lambda busy: setattr(app, "busy_snapshot", busy)
        app._append_log = lambda *_args: None

        with TemporaryDirectory() as temporary_directory:
            source = Path(temporary_directory) / "source.md"
            output = Path(temporary_directory) / "out"
            source.write_text("# source", encoding="utf-8")
            app.files = [str(source)]
            app.output_dir.set(str(output))

            with patch.object(gui.threading, "Thread", Thread):
                with patch.object(gui.messagebox, "showwarning"):
                    app.start_conversion()

            app.files.clear()
            app.pdf_mode.set("layout")
            thread = started[0]
            self.assertIsInstance(thread.args[0], tuple)

            with patch.object(worker.pythoncom, "CoInitialize"), patch.object(
                worker.pythoncom, "CoUninitialize"
            ), patch.object(worker.time, "sleep"), patch.object(
                worker.converter, "prepare_output_dir", return_value=output
            ) as prepare_output_dir, patch.object(
                worker.converter, "create_hwp_object", return_value=Hwp()
            ), patch.object(worker.converter, "as_path", return_value=source), patch.object(
                worker.converter, "build_output_path", return_value=output / "source.hwpx"
            ), patch.object(worker.converter, "convert_file", return_value={}), patch.object(
                worker.converter, "record_output_file"
            ):
                thread.target(*thread.args)

            self.assertEqual(prepare_output_dir.call_args.args[0], str(output))
            self.assertEqual(
                [app.messages.get_nowait() for _ in range(app.messages.qsize())],
                [
                    ("progress", 0, 1, "source.md"),
                    ("log", "변환 중: source.md → source.hwpx", None),
                    ("progress", 1, 1, "source.md"),
                    ("log", "완료: source.hwpx", "ok"),
                    ("done", 1, []),
                ],
            )
            self.assertEqual(quit_calls, [True])


if __name__ == "__main__":
    unittest.main()
