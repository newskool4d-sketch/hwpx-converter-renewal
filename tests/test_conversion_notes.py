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


if __name__ == "__main__":
    unittest.main()
