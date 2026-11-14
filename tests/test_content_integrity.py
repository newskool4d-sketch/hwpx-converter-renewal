"""내용 무결성 회귀: 변환이 원문 글자·셀을 조용히 바꾸거나 지우면 안 된다."""
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import anyway_to_hwpx_com as converter
import table_hwpx_postprocess as postprocess


class InlineTextPreservationTests(unittest.TestCase):
    def test_markdown_keeps_angle_bracket_text(self):
        self.assertEqual(
            converter._clean_inline("<붙임 1> 참가 신청서 및 <표 2> 참조"),
            "<붙임 1> 참가 신청서 및 <표 2> 참조",
        )
        self.assertEqual(
            converter._clean_inline("점수 < 60 이면 재시험, 점수 > 90 이면 우수"),
            "점수 < 60 이면 재시험, 점수 > 90 이면 우수",
        )

    def test_markdown_still_strips_real_markup(self):
        self.assertEqual(converter._clean_inline("앞 <span class='x'>강조</span> 뒤<!-- 메모 -->"), "앞 강조 뒤")
        self.assertEqual(converter._clean_inline("줄1<br>줄2<BR/>줄3"), "줄1 줄2 줄3")
        self.assertEqual(converter._clean_inline("**굵게** _기울임_ `코드`"), "굵게 기울임 코드")

    def test_markdown_keeps_identifiers_and_multiplication(self):
        self.assertEqual(converter._clean_inline("plan_2026_final.hwpx"), "plan_2026_final.hwpx")
        self.assertEqual(converter._clean_inline("3*4*5=60"), "3*4*5=60")

    def test_plain_text_is_not_parsed_as_markdown(self):
        blocks = converter.parse_plain_text("<별지 제1호 서식>\nA_1_B 와 *별표* 표기\n")
        self.assertEqual([block["text"] for block in blocks], ["<별지 제1호 서식>", "A_1_B 와 *별표* 표기"])

    def test_csv_cells_are_kept_verbatim(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "s.csv"
            path.write_text("코드,비고\nA_1_B,<미정>\n", encoding="utf-8")
            block = converter.parse_csv_file(path)[0]
        self.assertEqual(block["rows"], [["A_1_B", "<미정>"]])

    def test_html_text_is_kept_verbatim(self):
        blocks = converter.parse_html("<p>점수 &lt; 60 또는 a_1_b</p>")
        self.assertEqual(blocks[0]["text"], "점수 < 60 또는 a_1_b")


class OfficialNormalizationBoundaryTests(unittest.TestCase):
    def _amount(self, text):
        return converter.normalize_official_amounts([{"type": "p", "text": text}])[0]["text"]

    def _date(self, text):
        return converter.normalize_official_dates([{"type": "p", "text": text}])[0]["text"]

    def test_non_amount_words_are_untouched(self):
        for text in (
            "청렴 3원칙을 준수한다",
            "AI 교육 2026 원년 선포",
            "주 3 원격수업",
            "환율 1,385.5원",
            "단가 0.5원",
            "1234,567원",
        ):
            with self.subTest(text=text):
                self.assertEqual(self._amount(text), text)

    def test_amounts_with_particles_are_still_normalized(self):
        self.assertEqual(self._amount("10,000원인 경우"), "금10,000원(금일만원)인 경우")
        self.assertEqual(self._amount("5000원을 지급"), "금5000원(금오천원)을 지급")
        self.assertEqual(self._amount("3000원가량"), "금3000원(금삼천원)가량")

    def test_non_date_tokens_are_untouched(self):
        for text in (
            "붙임 계획서_2026.03.22.hwpx 1부.",
            "문서번호 2026.12.31.001",
            "규격 1200.5.3mm",
        ):
            with self.subTest(text=text):
                self.assertEqual(self._date(text), text)

    def test_dates_are_still_normalized(self):
        self.assertEqual(self._date("일시: 2026.3.22 행사"), "일시: 2026. 3. 22. 행사")
        self.assertEqual(self._date("2026.03.22.(일) 14:00"), "2026. 3. 22.(일) 14:00")

    def test_header_value_without_text_is_normalized(self):
        block = {"type": "official_header", "label": "제목", "value": "2026.3.22 행사 113,560원"}
        dated = converter.normalize_official_dates([block])[0]
        self.assertEqual(dated["value"], "2026. 3. 22. 행사 113,560원")
        amount = converter.normalize_official_amounts([dated])[0]
        self.assertIn("금113,560원(금일십일만삼천오백육십원)", amount["value"])


class DocxMergeCoordinateTests(unittest.TestCase):
    def _grid(self, build):
        from docx import Document

        document = Document()
        table = build(document)
        return converter._docx_table_grid(table)

    def test_merge_rows_follow_removed_empty_row(self):
        def build(document):
            table = document.add_table(rows=4, cols=2)
            table.cell(0, 0).text, table.cell(0, 1).text = "h1", "h2"
            table.cell(2, 0).merge(table.cell(2, 1)).text = "합친셀"
            table.cell(3, 0).text, table.cell(3, 1).text = "왼", "오른"
            return table

        grid, merges = self._grid(build)
        self.assertEqual(grid, [["h1", "h2"], ["합친셀", ""], ["왼", "오른"]])
        self.assertEqual(merges, [[1, 0, 1, 2]])

    def test_vertical_merge_shrinks_when_covered_row_is_removed(self):
        def build(document):
            table = document.add_table(rows=4, cols=2)
            table.cell(0, 0).text, table.cell(0, 1).text = "h1", "h2"
            table.cell(1, 0).merge(table.cell(2, 0)).text = "A"
            table.cell(1, 1).text = "a1"
            table.cell(3, 0).text, table.cell(3, 1).text = "B", "b1"
            return table

        grid, merges = self._grid(build)
        self.assertEqual(grid, [["h1", "h2"], ["A", "a1"], ["B", "b1"]])
        self.assertEqual(merges, [])


class XlsxCoveredRowTests(unittest.TestCase):
    def test_fully_covered_row_keeps_following_rows_in_place(self):
        from openpyxl import Workbook

        workbook = Workbook()
        sheet = workbook.active
        sheet["A1"] = "예산 총괄"
        sheet.merge_cells("A1:C2")
        for row_index, values in enumerate((["구분", "금액", "비율"], ["강사료", 100, "50%"]), start=3):
            for col_index, value in enumerate(values, start=1):
                sheet.cell(row=row_index, column=col_index, value=value)
        block = converter._xlsx_table_block(sheet)
        self.assertEqual(block["header"], ["예산 총괄", "", ""])
        # 전부 가려진 2행은 셀 없는 행이 되어 한글이 열지 못하므로 빼고 병합을 1행으로 줄인다.
        self.assertEqual(block["rows"], [["구분", "금액", "비율"], ["강사료", "100", "50%"]])
        self.assertEqual(block["merged_cells"], [[0, 0, 1, 3]])


class FullyCoveredRowTests(unittest.TestCase):
    def test_html_rowspan_over_whole_row_leaves_no_cellless_row(self):
        block = converter.parse_html(
            "<table><tr><td rowspan='2' colspan='2'>제목</td></tr><tr></tr><tr><td>a</td><td>b</td></tr></table>"
        )[0]
        self.assertEqual([block["header"]] + block["rows"], [["제목", ""], ["a", "b"]])
        self.assertEqual(block["merged_cells"], [[0, 0, 1, 2]])

    def test_partial_rowspan_is_unchanged(self):
        block = converter.parse_html(
            "<table><tr><td rowspan='2'>A</td><td>b1</td></tr><tr><td>b2</td></tr></table>"
        )[0]
        self.assertEqual([block["header"]] + block["rows"], [["A", "b1"], ["", "b2"]])
        self.assertEqual(block["merged_cells"], [[0, 0, 2, 1]])


class CoveredCellTextGuardTests(unittest.TestCase):
    def _table(self, texts):
        hp = postprocess.HP_NS
        tbl = ET.Element(f"{{{hp}}}tbl")
        for row_index, row in enumerate(texts):
            tr = ET.SubElement(tbl, f"{{{hp}}}tr")
            for col_index, text in enumerate(row):
                tc = ET.SubElement(tr, f"{{{hp}}}tc")
                ET.SubElement(tc, f"{{{hp}}}cellAddr", {"rowAddr": str(row_index), "colAddr": str(col_index)})
                ET.SubElement(tc, f"{{{hp}}}t").text = text
        return tbl

    def test_merge_over_filled_cell_is_not_applied(self):
        tbl = self._table([["합친셀", ""], ["왼", "오른"]])
        spans = {(0, 0): [0, 0, 1, 2], (1, 0): [1, 0, 1, 2]}
        valid, dropped = postprocess._filter_spans_covering_text(tbl, spans)
        self.assertEqual(valid, {(0, 0): [0, 0, 1, 2]})
        self.assertEqual(dropped, [[1, 0, 1, 2]])


class EmptyResultTests(unittest.TestCase):
    def _parse(self, name, content):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / name
            path.write_text(content, encoding="utf-8")
            return converter.detect_and_parse(path)

    def test_empty_source_is_an_error_not_an_empty_document(self):
        with self.assertRaises(RuntimeError):
            self._parse("empty.md", "\n\n")
        with self.assertRaises(RuntimeError):
            self._parse("empty.html", "<html><body><img src='a.png'></body></html>")

    def test_leading_rule_without_closing_is_not_front_matter(self):
        blocks = converter.parse_markdown("---\n본문 첫 줄\n둘째 줄\n")
        self.assertEqual([block.get("text") for block in blocks if block["type"] == "p"], ["본문 첫 줄", "둘째 줄"])

    def test_front_matter_is_still_skipped(self):
        blocks = converter.parse_markdown("---\ntitle: x\n---\n본문\n")
        self.assertEqual([block.get("text") for block in blocks], ["본문"])

    def test_html_div_dl_and_deep_headings_are_kept(self):
        blocks = converter.parse_html(
            "<div>본문</div><div><p>문단</p><div>안쪽</div></div><h5>소제목</h5><dl><dt>용어</dt><dd>설명</dd></dl>"
        )
        self.assertEqual(
            [(block["type"], block["text"]) for block in blocks],
            [("p", "본문"), ("p", "문단"), ("p", "안쪽"), ("h", "소제목"), ("p", "용어"), ("p", "설명")],
        )


if __name__ == "__main__":
    unittest.main()
