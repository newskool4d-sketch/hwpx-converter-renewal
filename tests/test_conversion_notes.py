import contextlib
import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import anyway_to_hwpx_com as converter
from table_hwpx_styles import HWPML_ROOT_NAMESPACES


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


class OfficialNormalizationTests(unittest.TestCase):
    """공문 정규화(날짜·금액·표기 점검)와 '끝' 표시의 분리 — build_doc에 전달되는 blocks로 판정."""

    def setUp(self):
        converter.pop_conversion_notes()

    def _captured_blocks(self, **kwargs):
        captured = []
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "s.md"
            source.write_text("2026.3.22 행사\n\n강사료 400,000원", encoding="utf-8")
            with (
                patch.object(converter, "build_doc", side_effect=lambda _hwp, blocks: captured.append(blocks)),
                patch.object(converter.time, "sleep", return_value=None),
            ):
                result = converter.convert_file(_FakeHwp(), source, Path(tmp) / "s.hwpx", **kwargs)
        return captured[0], result["notes"]

    # 특성화: --insert-end-mark 현행 의미(정규화 + '끝') 고정. 날짜 뒤 공백은 N17 수정(사용자 결정 2026-09-28)으로 보존
    def test_insert_end_mark_keeps_current_normalization_and_end_mark(self):
        blocks, _ = self._captured_blocks(insert_end_mark=True)
        self.assertEqual(blocks, [
            {"type": "p", "text": "2026. 3. 22. 행사"},
            {"type": "p", "text": "강사료 금400,000원(금사십만원)  끝."},
        ])

    def test_official_normalizes_without_end_mark(self):
        blocks, _ = self._captured_blocks(official=True)
        self.assertEqual(blocks, [
            {"type": "p", "text": "2026. 3. 22. 행사"},
            {"type": "p", "text": "강사료 금400,000원(금사십만원)"},
        ])

    def test_date_normalization_keeps_following_space(self):  # N17
        blocks = converter.normalize_official_dates([{"type": "p", "text": "2026.3.22 행사, 2026.3.23. 마감"}])
        self.assertEqual(blocks[0]["text"], "2026. 3. 22. 행사, 2026. 3. 23. 마감")

    def test_default_leaves_text_untouched(self):
        blocks, _ = self._captured_blocks()
        self.assertEqual(blocks, [{"type": "p", "text": "2026.3.22 행사"}, {"type": "p", "text": "강사료 400,000원"}])

    def test_cli_official_and_doc_type_reach_convert_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "s.md"
            source.write_text("본문", encoding="utf-8")
            with (
                contextlib.redirect_stdout(io.StringIO()),
                patch.object(converter, "create_hwp_object", return_value=_FakeHwp()),
                patch.object(converter, "convert_file", return_value={"notes": []}) as convert,
                patch.object(converter.time, "sleep", return_value=None),
            ):
                exit_code = converter.main([str(source), "-o", tmp, "--official", "--doc-type", "sihaengmun"])
        self.assertEqual(exit_code, 0)
        self.assertTrue(convert.call_args.kwargs["official"])
        self.assertEqual(convert.call_args.kwargs["doc_type"], "sihaengmun")


def _package(path, *, mimetype_first=True, broken_section=False, drop_rowcnt=False, bare_header=False):
    ns = " ".join(f'xmlns:{p}="{u}"' for p, u in HWPML_ROOT_NAMESPACES.items())
    decl = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
    tbl = '<hp:tbl colCnt="1"/>' if drop_rowcnt else '<hp:tbl rowCnt="1" colCnt="1"/>'
    section = f"{decl}<hs:sec {ns}><hp:p>{tbl}</hp:p></hs:sec>"
    if broken_section:
        section = section.replace("</hs:sec>", "")
    header_ns = f'xmlns:hh="{HWPML_ROOT_NAMESPACES["hh"]}"' if bare_header else ns
    header = f"{decl}<hh:head {header_ns}/>"
    entries = [
        ("mimetype", "application/hwp+zip", zipfile.ZIP_STORED),
        ("Contents/header.xml", header, zipfile.ZIP_DEFLATED),
        ("Contents/section0.xml", section, zipfile.ZIP_DEFLATED),
    ]
    if not mimetype_first:
        entries.append(entries.pop(0))
    with zipfile.ZipFile(path, "w") as zf:
        for name, text, method in entries:
            zf.writestr(zipfile.ZipInfo(name), text, compress_type=method)


class SelfCheckTests(unittest.TestCase):
    def _check(self, **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.hwpx"
            _package(path, **kwargs)
            return converter.self_check_hwpx(path)

    def _assert_flagged(self, notes, needle):
        self.assertTrue(notes, "자가검증이 문제를 보고해야 함")
        self.assertTrue(all(n.startswith("[확인 필요] 산출물 자가검증") for n in notes), notes)
        self.assertTrue(any(needle in n for n in notes), notes)

    def test_clean_package_has_no_findings(self):
        self.assertEqual(self._check(), [])

    def test_mimetype_must_be_first_and_stored(self):
        self._assert_flagged(self._check(mimetype_first=False), "mimetype")

    def test_broken_xml_is_reported(self):
        self._assert_flagged(self._check(broken_section=True), "section0.xml")

    def test_table_without_rowcnt_is_reported(self):
        self._assert_flagged(self._check(drop_rowcnt=True), "rowCnt")

    def test_missing_root_namespaces_are_reported(self):
        self._assert_flagged(self._check(bare_header=True), "네임스페이스")

    def test_non_zip_output_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.hwpx"
            path.write_bytes(b"saved")
            self._assert_flagged(converter.self_check_hwpx(path), "ZIP")

    def test_convert_file_appends_self_check_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "s.md"
            source.write_text("본문", encoding="utf-8")
            with (
                patch.object(converter, "build_doc", return_value=None),
                patch.object(converter.time, "sleep", return_value=None),
            ):
                result = converter.convert_file(_FakeHwp(), source, Path(tmp) / "s.hwpx")
        self.assertTrue(any(n.startswith("[확인 필요] 산출물 자가검증") for n in result["notes"]), result["notes"])


class VersionTests(unittest.TestCase):
    def test_version_string_follows_release_date_scheme(self):
        self.assertRegex(converter.__version__, r"^\d{4}\.\d{2}\.\d{2}(\+dev)?$")

    def test_cli_version_prints_version_and_exits_zero(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            converter.main(["--version"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn(converter.__version__, output.getvalue())


class MarkdownMediaTests(unittest.TestCase):
    def setUp(self):
        converter.pop_conversion_notes()

    def test_image_with_alt_text_leaves_no_residue(self):
        blocks = converter.parse_markdown("![현황 그래프](chart.png)\n\n본문")
        self.assertEqual(blocks, [{"type": "p", "text": "본문"}])

    def test_inline_image_and_link_cleanup(self):
        self.assertEqual(converter._clean_inline("앞 ![그림](a.png)뒤 [안내](https://x.kr)"), "앞 뒤 안내")

    def test_media_counts_become_notes_excluding_code_blocks(self):
        converter.parse_markdown("![a](a.png) [링크](https://x.kr)\n```\n![b](b.png)\n```\n본문")
        notes = converter.pop_conversion_notes()
        self.assertEqual(notes, [
            "[확인 필요] Markdown 이미지 1개 미삽입(이미지 삽입 미지원) — 필요 시 한글에서 직접 삽입",
            "[참고] Markdown 링크 1개는 표시 텍스트만 유지(URL 제외)",
        ])

    def test_plain_markdown_adds_no_media_notes(self):
        converter.parse_markdown("# 제목\n\n본문")
        self.assertEqual(converter.pop_conversion_notes(), [])


if __name__ == "__main__":
    unittest.main()
