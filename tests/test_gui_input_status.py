from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import gui_conversion_worker as worker
import gui_input_status
from gui_conversion_worker import note_log_tag
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


class _Progress:
    def configure(self, **kwargs):
        self.config = kwargs


class _QuitOnlyHwp:
    def Quit(self):
        return None


class _FinishApp(_App):
    def __init__(self) -> None:
        super().__init__()
        self.progress = _Progress()
        self.output_dir = _Value()
        self.busy_states: list[bool] = []

    def _set_busy(self, busy: bool) -> None:
        self.busy_states.append(busy)


class FinishConversionTests(unittest.TestCase):
    def test_note_tags_follow_prefix_severity(self) -> None:
        self.assertEqual(note_log_tag("[확인 필요] Markdown 이미지 1개 미삽입"), "err")
        self.assertEqual(note_log_tag("[경고] 줄 간격 후처리 실패: x"), "warn")
        self.assertEqual(note_log_tag("[표기 점검] '및' 사용"), "info")
        self.assertEqual(note_log_tag("[참고] 표 열 너비"), "muted")

    def test_notation_notes_do_not_mark_file_as_warned(self) -> None:
        messages = []
        snapshot = worker.ConversionSnapshot(
            files=("a.md",), output_dir="out", empty_output_folder=False, insert_end_mark=True, pdf_mode="layout"
        )
        with (
            patch.object(worker.pythoncom, "CoInitialize"),
            patch.object(worker.pythoncom, "CoUninitialize"),
            patch.object(worker.time, "sleep"),
            patch.object(worker.converter, "prepare_output_dir", return_value=Path("out")),
            patch.object(worker.converter, "create_hwp_object", return_value=_QuitOnlyHwp()),
            patch.object(worker.converter, "as_path", return_value=Path("a.md")),
            patch.object(worker.converter, "build_output_path", return_value=Path("out/a.hwpx")),
            patch.object(worker.converter, "convert_file", return_value={"notes": ["[표기 점검] '및' 사용"]}),
            patch.object(worker.converter, "record_output_file"),
        ):
            worker.run_conversion(snapshot, messages.append)
        self.assertEqual(messages[-1], ("done", 1, [], []))
        self.assertIn(("log", "[표기 점검] '및' 사용", "info"), messages)

    def test_security_module_warning_reaches_log(self) -> None:  # N16
        warning = "[확인 필요] 한글 보안 모듈 등록 실패 — 테스트"

        def fake_create(visible=True, warn=None):
            if warn is not None:
                warn(warning)
            return _QuitOnlyHwp()

        messages = []
        snapshot = worker.ConversionSnapshot(
            files=(), output_dir="out", empty_output_folder=False, insert_end_mark=False, pdf_mode="layout"
        )
        with (
            patch.object(worker.pythoncom, "CoInitialize"),
            patch.object(worker.pythoncom, "CoUninitialize"),
            patch.object(worker.time, "sleep"),
            patch.object(worker.converter, "prepare_output_dir", return_value=Path("out")),
            patch.object(worker.converter, "create_hwp_object", side_effect=fake_create),
        ):
            worker.run_conversion(snapshot, messages.append)
        self.assertIn(("log", warning, "err"), messages)

    def test_warned_files_produce_warning_summary_instead_of_plain_success(self) -> None:
        app = _FinishApp()
        with patch.object(gui_input_status.messagebox, "askyesno", return_value=False) as ask:
            gui_input_status.finish_conversion(app, 2, [], ["a.md"])

        self.assertIn("확인 필요 1개", app.status.value)
        self.assertEqual(ask.call_args.args[0], "변환 완료(확인 필요)")
        self.assertIn("a.md", ask.call_args.args[1])

    def test_clean_run_keeps_plain_success_dialog(self) -> None:
        app = _FinishApp()
        with patch.object(gui_input_status.messagebox, "askyesno", return_value=False) as ask:
            gui_input_status.finish_conversion(app, 2, [], [])

        self.assertEqual(app.status.value, "전체 변환 완료: 2개")
        self.assertEqual(ask.call_args.args[0], "변환 완료")


if __name__ == "__main__":
    unittest.main()
