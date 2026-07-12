from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from gui_file_intake import add_input_paths
from gui_input_status import report_input_result


class _Value:
    def __init__(self) -> None:
        self.value = ""

    def set(self, value: str) -> None:
        self.value = value


class _App:
    def __init__(self) -> None:
        self.files: list[str] = []
        self.status = _Value()
        self.logs: list[tuple[str, str]] = []

    def _append_log(self, text: str, tag: str) -> None:
        self.logs.append((text, tag))


class GuiInputStatusTests(unittest.TestCase):
    def test_rejected_only_input_keeps_reason_visible_in_error_color(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            unsupported = Path(temporary_directory) / "source.rtf"
            unsupported.write_text("unsupported", encoding="utf-8")
            result = add_input_paths(
                (str(unsupported),),
                (),
                (".md", ".pdf"),
                is_busy=False,
                output_directory="",
            )
            app = _App()

            report_input_result(app, result)

        self.assertIn("거부 1개", app.status.value)
        self.assertEqual(app.logs, [(app.status.value, "err")])


if __name__ == "__main__":
    unittest.main()
