import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import anyway_to_hwpx_com as converter


class _FakeDocument:
    def Close(self, isDirty=False):
        return None


class _FakeDocuments:
    def __init__(self):
        self.docs = []

    @property
    def Count(self):
        return len(self.docs)

    def Add(self, isTab=False):
        self.docs.append(_FakeDocument())

    def Item(self, index):
        return self.docs[index]


class _FakeHwp:
    """SaveAs가 ZIP이 아닌 바이트를 쓰므로 모든 XML 후처리가 실패한다."""

    def __init__(self):
        self.XHwpDocuments = _FakeDocuments()

    def SaveAs(self, output_path, format_name, option):
        Path(output_path).write_bytes(b"saved")

    def Quit(self):
        return None


BLOCKS = [{"type": "p", "text": "본문"}, {"type": "table", "header": ["구분"], "rows": [["값"]]}]


class PostprocessNoteRoutingTests(unittest.TestCase):
    def setUp(self):
        converter.pop_conversion_notes()

    def test_every_postprocess_failure_surfaces_in_result_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "sample.md"
            source.write_text("# 제목", encoding="utf-8")
            with (
                patch.object(converter, "detect_and_parse", return_value=list(BLOCKS)),
                patch.object(converter, "build_doc", return_value=None),
                patch.object(converter.time, "sleep", return_value=None),
            ):
                result = converter.convert_file(_FakeHwp(), source, Path(tmp) / "sample.hwpx")

        notes = result["notes"]
        for label in ("페이지 여백", "표 후처리", "목록 내어쓰기", "본문 단락 paraPr", "줄 간격", "단락 간격"):
            self.assertTrue(
                any(note.startswith("[경고]") and label in note for note in notes),
                f"{label} 경고 누락: {notes}",
            )

    def test_main_prints_each_note_exactly_once(self):
        def fake_parse(*_args, **_kwargs):
            converter._add_conversion_note("[참고] 테스트 노트")
            return [{"type": "p", "text": "본문"}]

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "sample.md"
            source.write_text("# 제목", encoding="utf-8")
            stdout, stderr = io.StringIO(), io.StringIO()
            with (
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
                patch.object(converter, "create_hwp_object", return_value=_FakeHwp()),
                patch.object(converter, "detect_and_parse", side_effect=fake_parse),
                patch.object(converter, "build_doc", return_value=None),
                patch.object(converter.time, "sleep", return_value=None),
            ):
                exit_code = converter.main([str(source), "-o", tmp])

        self.assertEqual(exit_code, 0)
        self.assertEqual((stdout.getvalue() + stderr.getvalue()).count("[참고] 테스트 노트"), 1)


class _Action:
    def CreateSet(self):
        return self

    def GetDefault(self, _pset):
        return None

    def SetItem(self, _name, _value):
        return None

    def Execute(self, _pset):
        return True


class _HAction:
    def GetDefault(self, _name, _hset):
        return None

    def Execute(self, _name, _hset):
        return True

    def Run(self, _name):
        return True


class _InsertText:
    HSet = object()
    Text = ""


class _ParameterSets:
    HInsertText = _InsertText()


class _TableHwp:
    """TableColWidth 액션이 None(미지원)이거나 예외를 내는 한글 COM 대역."""

    def __init__(self, col_width_error=None):
        self.col_width_requests = 0
        self.col_width_error = col_width_error
        self.HAction = _HAction()
        self.HParameterSet = _ParameterSets()

    def CreateAction(self, name):
        if name == "TableColWidth":
            self.col_width_requests += 1
            if self.col_width_error is not None:
                raise self.col_width_error
            return None
        return _Action()


TWO_TABLES = [
    {"type": "table", "header": ["구분", "내용"], "rows": [["가", "나"]]},
    {"type": "table", "header": ["항목", "비고"], "rows": [["다", "라"]]},
]


class TableColWidthNoteTests(unittest.TestCase):
    def setUp(self):
        converter.pop_conversion_notes()

    def test_unavailable_action_is_probed_once_and_reported_as_info(self):
        hwp = _TableHwp()
        converter.build_doc(hwp, TWO_TABLES)
        notes = converter.pop_conversion_notes()

        self.assertEqual(hwp.col_width_requests, 1)
        self.assertEqual(
            [n for n in notes if "TableColWidth" in n],
            ["[참고] 표 열 너비: 이 한글 버전은 TableColWidth 미지원 — XML 후처리로 적용"],
        )
        self.assertFalse(any(n.startswith("[경고] 열 너비") for n in notes))

    def test_unexpected_action_error_is_reported_as_warning(self):
        hwp = _TableHwp(col_width_error=RuntimeError("COM 오류"))
        converter.build_doc(hwp, TWO_TABLES[:1])
        notes = converter.pop_conversion_notes()

        self.assertIn("[경고] 열 너비 조정 실패: COM 오류", notes)


if __name__ == "__main__":
    unittest.main()
