import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET

import anyway_to_hwpx_com as converter


HP_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"
NS = {"hp": HP_NS}


def hp(name):
    return f"{{{HP_NS}}}{name}"


def make_hwpx_with_section(path, section_xml):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("Contents/section0.xml", section_xml.encode("utf-8"))


def read_section(path):
    with zipfile.ZipFile(path, "r") as zf:
        return ET.fromstring(zf.read("Contents/section0.xml"))


def table_xml(rows=2, cols=3, include_para_pr=True, include_missing_cell_nodes=False):
    cells = []
    for row in range(rows):
        for col in range(cols):
            para_pr = "<hp:paraPr spaceBefore=\"999\" spaceAfter=\"999\" />" if include_para_pr else ""
            cell_sz = "" if include_missing_cell_nodes and row == rows - 1 and col == cols - 1 else "<hp:cellSz width=\"1\" height=\"1\" />"
            cells.append(
                f"<hp:tc>"
                f"<hp:cellAddr rowAddr=\"{row}\" colAddr=\"{col}\" />"
                f"{cell_sz}"
                f"<hp:subList>"
                f"<hp:p>{para_pr}<hp:run><hp:t>cell</hp:t></hp:run></hp:p>"
                f"</hp:subList>"
                f"</hp:tc>"
            )
    return (
        f"<?xml version=\"1.0\" encoding=\"utf-8\"?>"
        f"<hp:sec xmlns:hp=\"{HP_NS}\">"
        f"<hp:p><hp:run><hp:t>before</hp:t></hp:run></hp:p>"
        f"<hp:tbl rowCnt=\"{rows}\" colCnt=\"{cols}\">"
        f"<hp:sz width=\"{converter.TABLE_TOTAL_WIDTH}\" height=\"1\" />"
        f"{''.join(cells)}"
        f"</hp:tbl>"
        f"<hp:p><hp:paraPr spaceBefore=\"0\" spaceAfter=\"999\" /><hp:run><hp:t>after</hp:t></hp:run></hp:p>"
        f"</hp:sec>"
    )


class ParserTests(unittest.TestCase):
    def test_markdown_detects_heading_table_and_list(self):
        blocks = converter.parse_markdown(
            "# 제목\n\n"
            "| 이름 | 값 |\n"
            "|---|---|\n"
            "| 테스트 | 1 |\n\n"
            "- 항목\n"
        )

        self.assertEqual(blocks[0], {"type": "h", "level": 1, "text": "제목"})
        self.assertEqual(blocks[1]["type"], "table")
        self.assertEqual(blocks[1]["header"], ["이름", "값"])
        self.assertEqual(blocks[1]["rows"], [["테스트", "1"]])
        self.assertEqual(blocks[2]["type"], "li")
        self.assertEqual(blocks[2]["text"], "• 항목")

    def test_markdown_table_keeps_escaped_pipe_inside_cell(self):
        blocks = converter.parse_markdown(
            "| 이름 | 값 |\n"
            "|---|---|\n"
            "| 홍\\|길동 | 1 |\n"
        )

        self.assertEqual(blocks[0]["type"], "table")
        self.assertEqual(blocks[0]["rows"], [["홍|길동", "1"]])

    def test_markdown_table_pads_uneven_rows(self):
        blocks = converter.parse_markdown(
            "| 이름 | 값 | 비고 |\n"
            "|---|---|---|\n"
            "| 홍길동 | 1 |\n"
        )

        self.assertEqual(blocks[0]["type"], "table")
        self.assertEqual(blocks[0]["header"], ["이름", "값", "비고"])
        self.assertEqual(blocks[0]["rows"], [["홍길동", "1", ""]])

    def test_odl_table_joins_nested_cell_content(self):
        data = {
            "kids": [
                {
                    "type": "table",
                    "rows": [
                        {
                            "cells": [
                                {
                                    "kids": [
                                        {"type": "paragraph", "content": "항목"},
                                    ],
                                },
                            ],
                        },
                        {
                            "cells": [
                                {
                                    "kids": [
                                        {"type": "paragraph", "content": "본문"},
                                        {
                                            "type": "text block",
                                            "kids": [
                                                {"type": "paragraph", "content": "세부"},
                                                {
                                                    "type": "list",
                                                    "list items": [
                                                        {"content": "목록"},
                                                    ],
                                                },
                                            ],
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
            ],
        }

        blocks = converter._odl_data_to_blocks(data)

        self.assertEqual(blocks[0]["type"], "table")
        self.assertEqual(blocks[0]["header"], ["항목"])
        self.assertEqual(blocks[0]["rows"], [["본문 세부 목록"]])

    def test_pdfplumber_page_preserves_detected_tables(self):
        class FakeTable:
            bbox = (40, 80, 280, 150)

            def extract(self):
                return [
                    ["구분", "내용"],
                    ["1", "표 본문"],
                ]

        class FakePage:
            def find_tables(self):
                return [FakeTable()]

            def extract_words(self):
                return [
                    {"text": "표", "x0": 52, "x1": 64, "top": 98, "bottom": 110},
                    {"text": "밖", "x0": 50, "x1": 62, "top": 170, "bottom": 182},
                    {"text": "문단", "x0": 68, "x1": 92, "top": 170, "bottom": 182},
                ]

        blocks = converter._pdfplumber_page_to_blocks(FakePage())

        self.assertEqual(blocks[0]["type"], "table")
        self.assertEqual(blocks[0]["header"], ["구분", "내용"])
        self.assertEqual(blocks[0]["rows"], [["1", "표 본문"]])
        self.assertEqual(blocks[1], {"type": "p", "text": "밖 문단"})

    def test_pdfplumber_page_preserves_markdown_table_text_without_detected_table(self):
        class FakePage:
            def find_tables(self):
                return []

            def extract_words(self):
                return [
                    {"text": "|", "x0": 50, "x1": 55, "top": 90, "bottom": 102},
                    {"text": "구분", "x0": 60, "x1": 82, "top": 90, "bottom": 102},
                    {"text": "|", "x0": 86, "x1": 91, "top": 90, "bottom": 102},
                    {"text": "내용", "x0": 96, "x1": 118, "top": 90, "bottom": 102},
                    {"text": "|", "x0": 122, "x1": 127, "top": 90, "bottom": 102},
                ]

            def extract_text(self):
                return "| 구분 | 내용 |\n|---|---|\n| 1 | 표 본문 |"

        blocks = converter._pdfplumber_page_to_blocks(FakePage())

        self.assertEqual(blocks[0]["type"], "table")
        self.assertEqual(blocks[0]["header"], ["구분", "내용"])
        self.assertEqual(blocks[0]["rows"], [["1", "표 본문"]])

    def test_parse_pdf_uses_pdfplumber_structured_blocks_after_odl_failure(self):
        table_blocks = [{"type": "table", "header": ["구분", "내용"], "rows": [["1", "표 본문"]]}]

        with patch.object(converter, "extract_pdf_blocks_odl", side_effect=RuntimeError("odl unavailable")):
            with patch.object(converter, "extract_pdf_blocks_pdfplumber", return_value=table_blocks):
                with patch.object(converter, "try_kordoc_pdf_text") as kordoc_text:
                    blocks = converter.parse_pdf(Path("sample.pdf"))

        self.assertEqual(blocks, table_blocks)
        kordoc_text.assert_not_called()

    def test_parse_pdf_preserves_kordoc_markdown_table_fallback(self):
        markdown = "| 구분 | 내용 |\n|---|---|\n| 1 | 표 본문 |"

        with patch.object(converter, "extract_pdf_blocks_odl", side_effect=RuntimeError("odl unavailable")):
            with patch.object(converter, "extract_pdf_blocks_pdfplumber", side_effect=RuntimeError("plumber unavailable")):
                with patch.object(converter, "try_kordoc_pdf_text", return_value=markdown):
                    blocks = converter.parse_pdf(Path("sample.pdf"))

        self.assertEqual(blocks[0]["type"], "table")
        self.assertEqual(blocks[0]["header"], ["구분", "내용"])
        self.assertEqual(blocks[0]["rows"], [["1", "표 본문"]])

    def test_plain_text_detects_korean_numbered_list(self):
        blocks = converter.parse_plain_text("가. 첫째\n나. 둘째")

        self.assertEqual([block["type"] for block in blocks], ["li", "li"])
        self.assertEqual(blocks[0]["depth"], 2)
        self.assertEqual(blocks[0]["marker"], "가.")

    def test_plain_text_preserves_official_numbering_hierarchy(self):
        text = "\n".join(
            [
                "Ⅰ. 총칙",
                "1. 목적",
                "가. 방침",
                "1) 세부",
                "가) 대상",
                "(1) 내용",
                "(가) 방법",
                "① 확인",
                "㉮ 보완",
            ]
        )

        blocks = converter.parse_plain_text(text)

        self.assertEqual([block["depth"] for block in blocks], list(range(9)))
        self.assertEqual(
            [block["marker"] for block in blocks],
            ["Ⅰ.", "1.", "가.", "1)", "가)", "(1)", "(가)", "①", "㉮"],
        )
        self.assertEqual(blocks[0]["text"], "Ⅰ. 총칙")

    def test_official_numbering_normalizes_marker_spacing(self):
        blocks = converter.parse_markdown("1.   목적\n가.\t방침")

        self.assertEqual(blocks[0]["text"], "1. 목적")
        self.assertEqual(blocks[1]["text"], "가. 방침")

    def test_official_list_para_shape_uses_hanging_indent(self):
        top = converter.official_list_para_shape(0, "Ⅰ.")
        child = converter.official_list_para_shape(3, "1)")
        deep = converter.official_list_para_shape(99, "㉮")

        self.assertLess(top["indent_first"], 0)
        self.assertLess(child["indent_first"], 0)
        self.assertGreater(child["indent_left"], top["indent_left"])
        self.assertEqual(
            deep["indent_left"],
            converter.official_list_para_shape(converter.OFFICIAL_LIST_MAX_DEPTH, "㉮")["indent_left"],
        )

    def test_official_numbering_without_space_is_normalized(self):
        blocks = converter.parse_plain_text("1.목적\n가.방침")

        self.assertEqual([block["type"] for block in blocks], ["li", "li"])
        self.assertEqual([block["text"] for block in blocks], ["1. 목적", "가. 방침"])

    def test_year_like_decimal_text_is_not_official_numbering(self):
        blocks = converter.parse_plain_text("2026.6.9. 시행")

        self.assertEqual(blocks, [{"type": "p", "text": "2026.6.9. 시행"}])

    def test_official_list_para_shape_uses_left_alignment_and_fixed_marker_stops(self):
        top = converter.official_list_para_shape(0, "Ⅰ.")
        child = converter.official_list_para_shape(1, "1.")
        korean = converter.official_list_para_shape(2, "가.")

        self.assertEqual(top["align"], 0)
        self.assertEqual(child["align"], 0)
        self.assertGreater(child["indent_left"] + child["indent_first"], top["indent_left"] + top["indent_first"])
        self.assertGreater(korean["indent_left"] + korean["indent_first"], child["indent_left"] + child["indent_first"])
        self.assertEqual(top["text_gap"], top["indent_left"] - (top["indent_left"] + top["indent_first"]))


class OutputPathTests(unittest.TestCase):
    def test_build_output_path_avoids_existing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "sample.md"
            src.write_text("# sample", encoding="utf-8")
            (root / "sample.hwpx").write_text("", encoding="utf-8")
            (root / "sample - 2.hwpx").write_text("", encoding="utf-8")

            out = converter.build_output_path(src, root)

        self.assertEqual(out.name, "sample - 3.hwpx")

    def test_prepare_output_dir_refuses_unmanaged_nonempty_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "keep.txt").write_text("user data", encoding="utf-8")

            with self.assertRaises(RuntimeError):
                converter.prepare_output_dir(root, empty_output_folder=True)

            self.assertTrue((root / "keep.txt").exists())

    def test_prepare_output_dir_clears_only_manifest_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_output = root / "old.hwpx"
            old_output.write_text("old", encoding="utf-8")
            converter.write_output_manifest(root, [old_output])

            prepared = converter.prepare_output_dir(root, empty_output_folder=True)

            self.assertEqual(prepared, root.resolve())
            self.assertFalse(old_output.exists())
            self.assertTrue((root / converter.OUTPUT_MANIFEST_NAME).exists())

    def test_record_output_file_updates_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = converter.prepare_output_dir(tmp, empty_output_folder=True)
            output = root / "sample.hwpx"
            output.write_text("new", encoding="utf-8")

            converter.record_output_file(root, output)
            manifest = converter.read_output_manifest(root)

        self.assertEqual(manifest, ["sample.hwpx"])


class TableLayoutTests(unittest.TestCase):
    def test_column_widths_are_positive_and_sum_to_total(self):
        header = ["번호", "소속", "성명", "추진내용", "비고"]
        rows = [["1", "인천교육청", "홍길동", "세부 추진 내용을 길게 적습니다.", "확인"]]

        widths = converter.calc_col_widths(header, rows)

        self.assertEqual(sum(widths), converter.TABLE_TOTAL_WIDTH)
        self.assertTrue(all(width > 0 for width in widths))

    def test_row_heights_match_table_rows(self):
        header = ["번호", "추진내용"]
        rows = [["1", "긴 내용 " * 20]]
        widths = converter.calc_col_widths(header, rows)

        heights = converter.calc_row_heights(header, rows, widths)

        self.assertEqual(len(heights), 2)
        self.assertTrue(all(height >= converter.TABLE_MIN_ROW_HEIGHT for height in heights))

    def test_table_widths_expand_long_content_column_beyond_default_profile(self):
        header = ["항목", "내용"]
        short_rows = [["A", "짧음"]]
        long_rows = [["A", "긴 내용 " * 80]]

        short_widths = converter.calc_col_widths(header, short_rows)
        long_widths = converter.calc_col_widths(header, long_rows)

        self.assertEqual(sum(long_widths), converter.TABLE_TOTAL_WIDTH)
        self.assertGreater(long_widths[1], short_widths[1])
        self.assertLess(long_widths[0], short_widths[0])

    def test_table_spacing_changes_with_content_density(self):
        header = ["항목", "내용"]
        widths = converter.calc_col_widths(header, [["A", "긴 내용 " * 80]])

        compact_margin = converter.calc_table_cell_margin(header, [["A", "긴 내용 " * 80]], widths)
        relaxed_margin = converter.calc_table_cell_margin(header, [["A", "짧음"]], widths)
        compact_para = converter.calc_table_cell_para_space(header, [["A", "긴 내용 " * 80]], widths)
        relaxed_para = converter.calc_table_cell_para_space(header, [["A", "짧음"]], widths)

        self.assertLess(compact_margin["left"], relaxed_margin["left"])
        self.assertLess(compact_margin["top"], relaxed_margin["top"])
        self.assertLessEqual(compact_para["spaceAfter"], relaxed_para["spaceAfter"])

    def test_hwpx_postprocess_applies_table_spacing(self):
        header = ["번호", "추진내용", "비고"]
        rows = [["1", "긴 내용 " * 30, "확인"]]

        with tempfile.TemporaryDirectory() as tmp:
            hwpx_path = Path(tmp) / "table.hwpx"
            make_hwpx_with_section(hwpx_path, table_xml(rows=2, cols=3))

            converter.apply_table_layout_profiles(hwpx_path, [{"header": header, "rows": rows}])
            root = read_section(hwpx_path)

        cells = root.findall(".//hp:tc", NS)
        widths = [int(cell.find("hp:cellSz", NS).attrib["width"]) for cell in cells[:3]]
        heights = [int(cell.find("hp:cellSz", NS).attrib["height"]) for cell in cells]
        margin = root.find(".//hp:tbl/hp:cellMargin", NS)
        cell_para_pr = cells[0].find(".//hp:paraPr", NS)
        after_para_pr = root.findall("hp:p", NS)[1].find("hp:paraPr", NS)

        self.assertEqual(sum(widths), converter.TABLE_TOTAL_WIDTH)
        self.assertTrue(all(height >= converter.TABLE_MIN_ROW_HEIGHT for height in heights))
        self.assertGreater(heights[-1], heights[0])
        expected_margin = converter.calc_table_cell_margin(header, rows, widths)
        expected_para = converter.calc_table_cell_para_space(header, rows, widths)
        expected_after = converter.calc_table_after_para_space(header, rows, widths)

        self.assertEqual(margin.attrib, {key: str(value) for key, value in expected_margin.items()})
        self.assertEqual(cell_para_pr.attrib["spaceBefore"], "0")
        self.assertEqual(cell_para_pr.attrib["spaceAfter"], str(expected_para["spaceAfter"]))
        self.assertEqual(after_para_pr.attrib["spaceBefore"], str(expected_after["spaceBefore"]))
        self.assertEqual(after_para_pr.attrib["spaceAfter"], str(expected_after["spaceAfter"]))

    def test_hwpx_postprocess_handles_uneven_rows_and_missing_nodes(self):
        header = ["항목", "내용"]
        rows = [["짧음"], ["긴 내용 " * 80, "비고"]]

        with tempfile.TemporaryDirectory() as tmp:
            hwpx_path = Path(tmp) / "edge.hwpx"
            make_hwpx_with_section(
                hwpx_path,
                table_xml(rows=3, cols=2, include_para_pr=False, include_missing_cell_nodes=True),
            )

            converter.apply_table_layout_profiles(hwpx_path, [{"header": header, "rows": rows}])
            root = read_section(hwpx_path)

        cells = root.findall(".//hp:tc", NS)
        cell_sizes = [cell.find("hp:cellSz", NS) for cell in cells]
        heights = [int(cell_size.attrib["height"]) for cell_size in cell_sizes if cell_size is not None]

        self.assertEqual(len(cell_sizes), 6)
        self.assertTrue(all(cell_size is not None for cell_size in cell_sizes))
        self.assertTrue(all(height >= converter.TABLE_MIN_ROW_HEIGHT for height in heights))
        self.assertGreater(max(heights), converter.TABLE_MIN_ROW_HEIGHT)

    def test_column_widths_scale_to_large_table_width(self):
        header = ["항목", "값"]
        rows = [["참여", "10"]]
        large_total = 41954  # HWP COM 기본 표 너비

        widths = converter.calc_col_widths(header, rows, large_total)

        self.assertEqual(sum(widths), large_total)
        self.assertTrue(all(w > 0 for w in widths))
        # default 2-column profile [28, 72]: col0 should be roughly 28%
        self.assertGreater(widths[0], int(large_total * 0.20))
        self.assertLess(widths[0], int(large_total * 0.40))

    def test_column_widths_scale_proportionally_across_totals(self):
        header = ["번호", "내용", "비고"]
        rows = [["1", "설명", "참고"]]

        w14 = converter.calc_col_widths(header, rows, converter.TABLE_TOTAL_WIDTH)
        w42 = converter.calc_col_widths(header, rows, 41954)

        # proportions should be similar across different totals
        r14 = [w / sum(w14) for w in w14]
        r42 = [w / sum(w42) for w in w42]
        for r1, r2 in zip(r14, r42):
            self.assertAlmostEqual(r1, r2, delta=0.05)

    def test_legacy_width_profile_wrapper_still_updates_widths(self):
        with tempfile.TemporaryDirectory() as tmp:
            hwpx_path = Path(tmp) / "legacy.hwpx"
            make_hwpx_with_section(hwpx_path, table_xml(rows=1, cols=2))

            converter.apply_table_width_profiles(hwpx_path, [["구분", "내용"]])
            root = read_section(hwpx_path)

        widths = [
            int(cell.find("hp:cellSz", NS).attrib["width"])
            for cell in root.findall(".//hp:tc", NS)
        ]

        self.assertEqual(sum(widths), converter.TABLE_TOTAL_WIDTH)
        self.assertLess(widths[0], widths[1])


HH_NS = "http://www.hancom.co.kr/hwpml/2011/head"
HP_PARA_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HC_NS = "http://www.hancom.co.kr/hwpml/2011/core"


def make_hwpx_with_header(path, header_xml):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("Contents/section0.xml", b"<root/>")
        zf.writestr("Contents/header.xml", header_xml.encode("utf-8"))


def make_list_header_xml(left_val, intent_val=0):
    """Build a minimal header.xml with one hh:paraPr having the given left value."""
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<hh:head xmlns:hh="{HH_NS}" xmlns:hp="{HP_PARA_NS}" xmlns:hc="{HC_NS}">'
        f'<hh:paraProperties>'
        f'<hh:paraPr id="20">'
        f'<hp:switch>'
        f'<hp:case hp:required-namespace="http://www.hancom.co.kr/hwpml/2016/HwpUnitChar">'
        f'<hh:margin>'
        f'<hc:intent value="{intent_val}" unit="HWPUNIT"/>'
        f'<hc:left value="{left_val}" unit="HWPUNIT"/>'
        f'</hh:margin>'
        f'</hp:case>'
        f'<hp:default>'
        f'<hh:margin>'
        f'<hc:intent value="{intent_val}" unit="HWPUNIT"/>'
        f'<hc:left value="{left_val * 2}" unit="HWPUNIT"/>'
        f'</hh:margin>'
        f'</hp:default>'
        f'</hp:switch>'
        f'</hh:paraPr>'
        f'</hh:paraProperties>'
        f'</hh:head>'
    )


def read_header_intents(path):
    with zipfile.ZipFile(path, "r") as zf:
        header = ET.fromstring(zf.read("Contents/header.xml"))
    intents = []
    for margin in header.iter(f"{{{HH_NS}}}margin"):
        intent = margin.find(f"{{{HC_NS}}}intent")
        if intent is not None:
            intents.append(int(intent.get("value", "0")))
    return intents


class ListHangingIndentTests(unittest.TestCase):
    def test_apply_sets_intent_for_known_depth(self):
        """apply_list_hanging_indents sets hc:intent for depth=1 (left=900)."""
        with tempfile.TemporaryDirectory() as tmp:
            hwpx_path = Path(tmp) / "test.hwpx"
            make_hwpx_with_header(hwpx_path, make_list_header_xml(left_val=900, intent_val=0))
            converter.apply_list_hanging_indents(hwpx_path)
            intents = read_header_intents(hwpx_path)
        # hp:case: -540, hp:default: -1080
        self.assertIn(-540, intents)
        self.assertIn(-1080, intents)

    def test_apply_does_not_touch_unknown_left(self):
        """apply_list_hanging_indents leaves unknown left values unchanged."""
        with tempfile.TemporaryDirectory() as tmp:
            hwpx_path = Path(tmp) / "test.hwpx"
            # left=1500 is a built-in style value, not in the map
            make_hwpx_with_header(hwpx_path, make_list_header_xml(left_val=1500, intent_val=0))
            converter.apply_list_hanging_indents(hwpx_path)
            intents = read_header_intents(hwpx_path)
        self.assertTrue(all(v == 0 for v in intents))

    def test_all_map_depths_produce_correct_intents(self):
        """Each depth's indent_left maps to the correct hc:intent via apply_list_hanging_indents."""
        expected = {
            620: -620,
            900: -540,
            1320: -600,
            1620: -540,
            2040: -600,
            2400: -600,
            2880: -720,
            3060: -540,
            3420: -540,
        }
        with tempfile.TemporaryDirectory() as tmp:
            for left_val, intent_expected in expected.items():
                hwpx_path = Path(tmp) / f"test_{left_val}.hwpx"
                make_hwpx_with_header(hwpx_path, make_list_header_xml(left_val=left_val, intent_val=0))
                converter.apply_list_hanging_indents(hwpx_path)
                intents = read_header_intents(hwpx_path)
                self.assertIn(
                    intent_expected, intents,
                    f"left={left_val}: expected intent {intent_expected} in {intents}",
                )


class OfficialHeaderParserTests(unittest.TestCase):
    def test_parses_all_three_header_keys(self):
        md = '수신: 교장선생님\n경유: 없음\n제목: 테스트 문서'
        blocks = converter.parse_markdown(md)
        self.assertEqual(len(blocks), 3)
        self.assertEqual(blocks[0], {'type': 'official_header', 'key': '수신', 'value': '교장선생님'})
        self.assertEqual(blocks[1], {'type': 'official_header', 'key': '경유', 'value': '없음'})
        self.assertEqual(blocks[2], {'type': 'official_header', 'key': '제목', 'value': '테스트 문서'})

    def test_parses_header_with_spaces_around_colon(self):
        md = '수신 : 광역시교육감'
        blocks = converter.parse_markdown(md)
        self.assertEqual(blocks[0], {'type': 'official_header', 'key': '수신', 'value': '광역시교육감'})

    def test_header_mixed_with_body_text(self):
        md = '수신: 원장님\n\n일반 본문 내용입니다.'
        blocks = converter.parse_markdown(md)
        types = [b['type'] for b in blocks]
        self.assertIn('official_header', types)
        self.assertIn('p', types)


class BulletHierarchyTests(unittest.TestCase):
    def test_bullet_after_official_item_is_one_level_deeper(self):
        md = '가. 추진 배경\n- 세부 사항'
        blocks = converter.parse_markdown(md)
        self.assertEqual(blocks[0]['depth'], 2)   # 가. → depth 2
        self.assertEqual(blocks[1]['marker'], '•')
        self.assertEqual(blocks[1]['depth'], 3)   # 하위 항목 → depth 3

    def test_indented_bullet_goes_deeper(self):
        md = '가. 추진 배경\n- 세부 사항\n  - 더 깊은 사항'
        blocks = converter.parse_markdown(md)
        self.assertEqual(blocks[1]['depth'], 3)
        self.assertEqual(blocks[2]['depth'], 4)   # 2칸 들여쓰기 → +1 단계

    def test_bullet_follows_most_recent_official_item(self):
        md = '1. 개요\n가. 배경\n1) 현황\n- 비고'
        blocks = converter.parse_markdown(md)
        self.assertEqual(blocks[2]['depth'], 3)   # 1) → depth 3
        self.assertEqual(blocks[3]['depth'], 4)   # 불릿 → depth 4

    def test_bullet_without_context_keeps_default_depth(self):
        blocks = converter.parse_markdown('- 단독 불릿')
        self.assertEqual(blocks[0]['depth'], 1)

    def test_bullet_after_heading_converted_official_item(self):
        md = '# 1. 개요\n- 주요 내용'
        blocks = converter.parse_markdown(md)
        self.assertEqual(blocks[0]['depth'], 1)   # heading → li (1. = depth 1)
        self.assertEqual(blocks[1]['depth'], 2)   # 불릿 → depth 2

    def test_plain_heading_resets_official_context(self):
        md = '가. 배경\n## 별첨\n- 항목'
        blocks = converter.parse_markdown(md)
        self.assertEqual(blocks[2]['depth'], 2)   # heading_level=2 기준 (직전 항목기호 무시)

    def test_bullet_depth_capped_at_max(self):
        md = '㉮ 최하위 항목\n- 불릿'
        blocks = converter.parse_markdown(md)
        self.assertEqual(blocks[0]['depth'], 8)
        self.assertEqual(blocks[1]['depth'], 8)   # 8 + 1 → cap 8

    def test_plain_text_bullet_follows_official_item(self):
        text = '가. 추진 배경\n- 세부 사항'
        blocks = converter.parse_plain_text(text)
        self.assertEqual(blocks[0]['depth'], 2)
        self.assertEqual(blocks[1]['depth'], 3)


class EndMarkBlockTests(unittest.TestCase):
    def test_text_block_gets_end_mark_on_same_line(self):
        blocks = [{'type': 'p', 'text': '보고합니다.'}]
        result = converter.append_end_mark_blocks(blocks)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['text'], '보고합니다.  끝.')

    def test_table_block_gets_end_mark_paragraph(self):
        blocks = [{'type': 'table', 'header': ['구분'], 'rows': [['내용']]}]
        result = converter.append_end_mark_blocks(blocks)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[1], {'type': 'p', 'text': ' 끝.'})

    def test_existing_end_mark_not_duplicated(self):
        blocks = [{'type': 'p', 'text': '보고합니다.  끝.'}]
        result = converter.append_end_mark_blocks(blocks)
        self.assertEqual(result[0]['text'], '보고합니다.  끝.')
        self.assertEqual(len(result), 1)

    def test_table_with_empty_row_marker_skipped(self):
        blocks = [{'type': 'table', 'header': ['구분'], 'rows': [['이하 빈칸']]}]
        result = converter.append_end_mark_blocks(blocks)
        self.assertEqual(len(result), 1)

    def test_attachment_gets_end_mark_on_same_line(self):
        blocks = [
            {'type': 'attachment', 'text': '붙임  1. 계획서 1부.'},
            {'type': 'attachment', 'text': '2. 서류 1부.', 'cont': True},
        ]
        result = converter.append_end_mark_blocks(blocks)
        self.assertEqual(result[-1]['text'], '2. 서류 1부.  끝.')

    def test_original_blocks_not_mutated(self):
        blocks = [{'type': 'p', 'text': '본문'}]
        converter.append_end_mark_blocks(blocks)
        self.assertEqual(blocks[0]['text'], '본문')


class OfficialDateTests(unittest.TestCase):
    def test_compact_date_normalized(self):
        blocks = [{'type': 'p', 'text': '관련: 공문(2026.3.2.)'}]
        result = converter.normalize_official_dates(blocks)
        self.assertEqual(result[0]['text'], '관련: 공문(2026. 3. 2.)')

    def test_date_without_trailing_dot_gets_one(self):
        blocks = [{'type': 'li', 'text': '가. 기간: 2026.4.10'}]
        result = converter.normalize_official_dates(blocks)
        self.assertEqual(result[0]['text'], '가. 기간: 2026. 4. 10.')

    def test_date_range_normalized(self):
        blocks = [{'type': 'p', 'text': '2026.4.10.~2026.4.12.'}]
        result = converter.normalize_official_dates(blocks)
        self.assertEqual(result[0]['text'], '2026. 4. 10.~2026. 4. 12.')

    def test_invalid_month_left_alone(self):
        blocks = [{'type': 'p', 'text': '버전 2026.13.99'}]
        result = converter.normalize_official_dates(blocks)
        self.assertEqual(result[0]['text'], '버전 2026.13.99')

    def test_already_normalized_unchanged(self):
        blocks = [{'type': 'p', 'text': '2026. 3. 22. 기준'}]
        result = converter.normalize_official_dates(blocks)
        self.assertEqual(result[0]['text'], '2026. 3. 22. 기준')

    def test_table_cells_not_touched(self):
        blocks = [{'type': 'table', 'header': ['일자'], 'rows': [['2026.3.2']]}]
        result = converter.normalize_official_dates(blocks)
        self.assertEqual(result[0]['rows'], [['2026.3.2']])


class AttachmentParserTests(unittest.TestCase):
    def test_attachment_head_and_continuation(self):
        md = '붙임  1. 운영 계획서 1부.\n2. 만족도 자료 1부.'
        blocks = converter.parse_markdown(md)
        self.assertEqual(blocks[0]['type'], 'attachment')
        self.assertEqual(blocks[0]['text'], '붙임  1. 운영 계획서 1부.')
        self.assertNotIn('cont', blocks[0])
        self.assertEqual(blocks[1]['type'], 'attachment')
        self.assertTrue(blocks[1]['cont'])

    def test_attachment_head_spacing_normalized(self):
        blocks = converter.parse_markdown('붙임 1. 계획서 1부.')
        self.assertEqual(blocks[0]['text'], '붙임  1. 계획서 1부.')

    def test_numbered_line_without_quantity_ends_attachment(self):
        md = '붙임  1. 계획서 1부.\n2. 일반 목록 항목'
        blocks = converter.parse_markdown(md)
        self.assertEqual(blocks[0]['type'], 'attachment')
        self.assertEqual(blocks[1]['type'], 'li')

    def test_blank_line_ends_attachment_context(self):
        md = '붙임  1. 계획서 1부.\n\n2. 별개 항목 1부.'
        blocks = converter.parse_markdown(md)
        self.assertEqual(blocks[0]['type'], 'attachment')
        self.assertEqual(blocks[1]['type'], 'li')

    def test_plain_text_attachment(self):
        blocks = converter.parse_plain_text('붙임  1. 보고서 1부.\n2. 사진 자료 1부.')
        self.assertEqual([b['type'] for b in blocks], ['attachment', 'attachment'])


class PlainTextTableTests(unittest.TestCase):
    def test_tab_separated_lines_become_table(self):
        text = '구분\t내용\t비고\n장소\t대강당\t강화\n예산\t350만원\t본예산'
        blocks = converter.parse_plain_text(text)
        self.assertEqual(blocks[0]['type'], 'table')
        self.assertEqual(blocks[0]['header'], ['구분', '내용', '비고'])
        self.assertEqual(len(blocks[0]['rows']), 2)

    def test_single_tab_line_stays_paragraph(self):
        blocks = converter.parse_plain_text('이름\t홍길동\n일반 문장입니다.')
        self.assertEqual([b['type'] for b in blocks], ['p', 'p'])

    def test_pipe_table_without_separator(self):
        text = '| 구분 | 내용 |\n| 장소 | 대강당 |'
        blocks = converter.parse_plain_text(text)
        self.assertEqual(blocks[0]['type'], 'table')
        self.assertEqual(blocks[0]['header'], ['구분', '내용'])
        self.assertEqual(blocks[0]['rows'], [['장소', '대강당']])

    def test_pipe_table_with_separator(self):
        text = '| 구분 | 내용 |\n|---|---|\n| 장소 | 대강당 |'
        blocks = converter.parse_plain_text(text)
        self.assertEqual(blocks[0]['type'], 'table')
        self.assertEqual(blocks[0]['rows'], [['장소', '대강당']])

    def test_uneven_tab_rows_padded(self):
        text = '구분\t내용\t비고\n장소\t대강당'
        blocks = converter.parse_plain_text(text)
        self.assertEqual(blocks[0]['type'], 'table')
        self.assertEqual(blocks[0]['rows'], [['장소', '대강당', '']])


class OdlTableGridTests(unittest.TestCase):
    @staticmethod
    def _cell(r, c, text, row_span=1, col_span=1):
        return {
            'row number': r, 'column number': c,
            'row span': row_span, 'column span': col_span,
            'content': text, 'kids': [],
        }

    def test_rowspan_keeps_columns_aligned(self):
        """세로 병합(1일 rowspan) 셀이 있어도 이후 행의 열이 밀리지 않는다."""
        element = {
            'type': 'table',
            'rows': [
                {'cells': [self._cell(1, 1, '일정', col_span=2), self._cell(1, 3, '내용')]},
                {'cells': [self._cell(2, 1, '1일', row_span=2), self._cell(2, 2, '10:00'), self._cell(2, 3, '개회')]},
                {'cells': [self._cell(3, 2, '12:00'), self._cell(3, 3, '점심')]},
            ],
        }
        grid, merges = converter._odl_table_grid(element)
        self.assertEqual(grid[0], ['일정', '', '내용'])
        self.assertEqual(grid[1], ['1일', '10:00', '개회'])
        self.assertEqual(grid[2], ['', '12:00', '점심'])  # 시간이 2열에 유지
        self.assertIn((0, 0, 1, 2), merges)  # 헤더 '일정' 가로 병합
        self.assertIn((1, 0, 2, 1), merges)  # '1일' 세로 병합

    def test_colspan_reserves_columns(self):
        element = {
            'type': 'table',
            'rows': [
                {'cells': [self._cell(1, 1, '내용', col_span=3)]},
                {'cells': [self._cell(2, 1, 'a'), self._cell(2, 2, 'b'), self._cell(2, 3, 'c')]},
            ],
        }
        grid, merges = converter._odl_table_grid(element)
        self.assertEqual(grid[0], ['내용', '', ''])
        self.assertEqual(grid[1], ['a', 'b', 'c'])
        self.assertEqual(merges, [(0, 0, 1, 3)])

    def test_missing_coords_falls_back_to_sequential(self):
        element = {
            'type': 'table',
            'rows': [
                {'cells': [{'content': '구분', 'kids': []}, {'content': '값', 'kids': []}]},
                {'cells': [{'content': 'A', 'kids': []}, {'content': '1', 'kids': []}]},
            ],
        }
        grid, merges = converter._odl_table_grid(element)
        self.assertEqual(grid, [['구분', '값'], ['A', '1']])
        self.assertEqual(merges, [])

    def test_empty_rows_removed(self):
        element = {
            'type': 'table',
            'rows': [
                {'cells': [self._cell(1, 1, '값')]},
                {'cells': [self._cell(2, 1, '')]},
            ],
        }
        grid, merges = converter._odl_table_grid(element)
        self.assertEqual(grid, [['값']])

    def test_merge_span_shrinks_when_covered_row_dropped(self):
        """병합 범위 안의 빈 행이 제거되면 rowspan도 함께 줄어든다."""
        element = {
            'type': 'table',
            'rows': [
                {'cells': [self._cell(1, 1, 'A', row_span=3), self._cell(1, 2, 'x')]},
                {'cells': [self._cell(2, 2, '')]},
                {'cells': [self._cell(3, 2, 'y')]},
            ],
        }
        grid, merges = converter._odl_table_grid(element)
        self.assertEqual(len(grid), 2)
        self.assertEqual(merges, [(0, 0, 2, 1)])


def make_merge_section_xml(rows=2, cols=2, width=1000, height=500):
    cells = []
    for r in range(rows):
        tcs = ''.join(
            f'<hp:tc borderFillIDRef="3"><hp:subList><hp:p/></hp:subList>'
            f'<hp:cellAddr colAddr="{c}" rowAddr="{r}"/>'
            f'<hp:cellSpan colSpan="1" rowSpan="1"/>'
            f'<hp:cellSz width="{width}" height="{height}"/></hp:tc>'
            for c in range(cols)
        )
        cells.append(f'<hp:tr>{tcs}</hp:tr>')
    return (
        '<hp:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">'
        f'<hp:tbl rowCnt="{rows}" colCnt="{cols}">{"".join(cells)}</hp:tbl></hp:sec>'
    )


class TableCellMergeTests(unittest.TestCase):
    def _apply(self, merges, rows=2, cols=2):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'test.hwpx'
            make_hwpx_with_section(path, make_merge_section_xml(rows=rows, cols=cols))
            layout = {'header': ['h'] * cols, 'rows': [['x'] * cols] * (rows - 1), 'merges': merges}
            converter.apply_table_cell_merges(path, [layout])
            return read_section(path)

    def test_rowspan_merge_removes_covered_cell(self):
        root = self._apply([(0, 0, 2, 1)])
        tcs = root.findall(f'.//{{{HP_NS}}}tc')
        self.assertEqual(len(tcs), 3)  # 4개 중 피병합 1개 제거
        anchor = tcs[0]
        span = anchor.find(f'{{{HP_NS}}}cellSpan')
        self.assertEqual(span.get('rowSpan'), '2')
        size = anchor.find(f'{{{HP_NS}}}cellSz')
        self.assertEqual(size.get('height'), '1000')  # 500 + 500
        self.assertEqual(size.get('width'), '1000')

    def test_colspan_merge_extends_width(self):
        root = self._apply([(0, 0, 1, 2)])
        tcs = root.findall(f'.//{{{HP_NS}}}tc')
        self.assertEqual(len(tcs), 3)
        span = tcs[0].find(f'{{{HP_NS}}}cellSpan')
        self.assertEqual(span.get('colSpan'), '2')
        size = tcs[0].find(f'{{{HP_NS}}}cellSz')
        self.assertEqual(size.get('width'), '2000')

    def test_no_merges_leaves_table_intact(self):
        root = self._apply([])
        self.assertEqual(len(root.findall(f'.//{{{HP_NS}}}tc')), 4)

    def test_out_of_range_merge_skipped(self):
        root = self._apply([(0, 0, 5, 5)])
        self.assertEqual(len(root.findall(f'.//{{{HP_NS}}}tc')), 4)


class OdlReadingOrderTests(unittest.TestCase):
    @staticmethod
    def _el(page, x0, y0, x1, y1, text):
        return {
            'type': 'paragraph', 'page number': page,
            'bounding box': [x0, y0, x1, y1], 'content': text, 'kids': [],
        }

    def test_two_column_page_reads_left_column_first(self):
        """y좌표 순으로 교차된 좌/우 열 요소를 좌열 전체 → 우열 전체로 재정렬."""
        els = [
            self._el(1, 50, 900, 350, 920, 'L1'),
            self._el(1, 450, 880, 750, 920, 'R1'),
            self._el(1, 50, 800, 350, 850, 'L2'),
            self._el(1, 450, 780, 750, 840, 'R2'),
            self._el(1, 50, 700, 350, 750, 'L3'),
            self._el(1, 450, 680, 750, 740, 'R3'),
        ]
        ordered = converter._odl_reading_order(els)
        self.assertEqual([e['content'] for e in ordered], ['L1', 'L2', 'L3', 'R1', 'R2', 'R3'])

    def test_full_width_title_stays_before_columns(self):
        els = [
            self._el(1, 50, 1000, 750, 1040, 'TITLE'),  # 중앙 가로지름
            self._el(1, 450, 880, 750, 920, 'R1'),
            self._el(1, 50, 900, 350, 920, 'L1'),
            self._el(1, 50, 800, 350, 850, 'L2'),
            self._el(1, 450, 780, 750, 840, 'R2'),
            self._el(1, 50, 700, 350, 750, 'L3'),
            self._el(1, 450, 680, 750, 740, 'R3'),
        ]
        ordered = converter._odl_reading_order(els)
        self.assertEqual(
            [e['content'] for e in ordered],
            ['TITLE', 'L1', 'L2', 'L3', 'R1', 'R2', 'R3'],
        )

    def test_single_column_keeps_original_order(self):
        els = [self._el(1, 50, 1000 - i * 50, 750, 1040 - i * 50, f'P{i}') for i in range(6)]
        ordered = converter._odl_reading_order(els)
        self.assertEqual([e['content'] for e in ordered], [f'P{i}' for i in range(6)])

    def test_missing_bbox_keeps_original_order(self):
        els = [
            self._el(1, 50, 900, 350, 920, 'A'),
            {'type': 'paragraph', 'content': 'NO-BBOX', 'kids': []},
            self._el(1, 450, 880, 750, 920, 'B'),
        ]
        ordered = converter._odl_reading_order(els)
        self.assertEqual([e.get('content') for e in ordered], ['A', 'NO-BBOX', 'B'])


class MissingLineRecoveryTests(unittest.TestCase):
    @staticmethod
    def _el(page, x0, y0, x1, y1, text):
        return {
            'type': 'paragraph', 'page number': page,
            'bounding box': [x0, y0, x1, y1], 'content': text, 'kids': [],
        }

    @staticmethod
    def _line(page, x0, x1, y_top, text):
        return {'page': page, 'x0': x0, 'x1': x1, 'y_top': y_top, 'text': text}

    def test_missing_line_inserted_by_y_position(self):
        els = [
            self._el(1, 50, 900, 400, 920, '8. 문항 줄기'),
            self._el(1, 50, 800, 400, 850, 'ㄹ. 마지막 보기'),
            self._el(1, 50, 600, 400, 650, '9. 다음 문항'),
        ]
        lines = [self._line(1, 50, 400, 750, '① ㄱ, ㄴ ② ㄱ, ㄷ ③ ㄴ, ㄷ ④ ㄴ, ㄹ ⑤ ㄷ, ㄹ')]
        merged, recovered, warnings = converter._merge_missing_lines(els, lines)
        self.assertEqual(len(recovered), 1)
        self.assertEqual(warnings, [])
        texts = [e['content'] for e in merged]
        self.assertEqual(texts.index('① ㄱ, ㄴ ② ㄱ, ㄷ ③ ㄴ, ㄷ ④ ㄴ, ㄹ ⑤ ㄷ, ㄹ'), 2)  # 보기 뒤, 9번 앞

    def test_present_line_with_spacing_difference_not_duplicated(self):
        els = [self._el(1, 50, 900, 400, 920, '① ㄱ,ㄴ ② ㄱ,ㄷ')]
        lines = [self._line(1, 50, 400, 910, '①  ㄱ, ㄴ  ②  ㄱ, ㄷ')]
        merged, recovered, _ = converter._merge_missing_lines(els, lines)
        self.assertEqual(recovered, [])
        self.assertEqual(len(merged), 1)

    def test_line_split_across_fragments_not_duplicated(self):
        els = [
            self._el(1, 50, 900, 400, 920, '① ㄱ, ㄴ ② ㄱ, ㄷ ③ ㄷ, ㄹ'),
            self._el(1, 50, 850, 400, 890, '④ ㄱ, ㄴ, ㄹ ⑤ ㄴ, ㄷ, ㄹ'),
        ]
        lines = [self._line(1, 50, 400, 905, '① ㄱ, ㄴ ② ㄱ, ㄷ ③ ㄷ, ㄹ ④ ㄱ, ㄴ, ㄹ ⑤ ㄴ, ㄷ, ㄹ')]
        merged, recovered, _ = converter._merge_missing_lines(els, lines)
        self.assertEqual(recovered, [])
        self.assertEqual(len(merged), 2)

    def test_short_and_page_number_lines_skipped(self):
        els = [self._el(1, 50, 900, 400, 920, '본문')]
        lines = [
            self._line(1, 50, 400, 800, '- 11 -'),
            self._line(1, 50, 400, 700, 'AB'),
        ]
        merged, recovered, warnings = converter._merge_missing_lines(els, lines)
        self.assertEqual(recovered, [])
        self.assertEqual(warnings, [])
        self.assertEqual(len(merged), 1)

    def test_running_header_on_three_pages_skipped(self):
        els = [
            self._el(1, 50, 900, 400, 920, '1쪽 본문'),
            self._el(2, 50, 900, 400, 920, '2쪽 본문'),
            self._el(3, 50, 900, 400, 920, '3쪽 본문'),
        ]
        lines = [
            self._line(p, 50, 400, 1000, '사회탐구 영역 (통합사회)')
            for p in (1, 2, 3)
        ]
        merged, recovered, warnings = converter._merge_missing_lines(els, lines)
        self.assertEqual(recovered, [])
        self.assertEqual(warnings, [])
        self.assertEqual(len(merged), 3)

    def test_line_on_empty_page_becomes_warning(self):
        els = [self._el(1, 50, 900, 400, 920, '본문')]
        lines = [self._line(2, 50, 400, 800, '근거 요소가 없는 페이지의 누락 줄')]
        merged, recovered, warnings = converter._merge_missing_lines(els, lines)
        self.assertEqual(recovered, [])
        self.assertEqual(len(warnings), 1)
        self.assertEqual(len(merged), 1)

    def test_two_column_line_inserted_in_right_column(self):
        els = [
            self._el(1, 50, 900, 350, 920, 'L1'),
            self._el(1, 50, 800, 350, 850, 'L2'),
            self._el(1, 50, 700, 350, 750, 'L3'),
            self._el(1, 450, 900, 750, 920, 'R1'),
            self._el(1, 450, 800, 750, 850, 'R2'),
            self._el(1, 450, 600, 750, 650, 'R3'),
        ]
        lines = [self._line(1, 450, 750, 720, '우측 열의 누락된 선택지 줄')]
        merged, recovered, _ = converter._merge_missing_lines(els, lines)
        self.assertEqual(len(recovered), 1)
        texts = [e['content'] for e in merged]
        # R2(y800)와 R3(y600) 사이
        self.assertEqual(texts.index('우측 열의 누락된 선택지 줄'), texts.index('R2') + 1)


class TwoColumnDetectionTests(unittest.TestCase):
    @staticmethod
    def _words(count, x0, x1, top_start=100):
        return [
            {'text': f'w{i}', 'x0': x0, 'x1': x1, 'top': top_start + i * 12, 'bottom': top_start + i * 12 + 10}
            for i in range(count)
        ]

    def test_two_column_layout_detected(self):
        words = self._words(30, 50, 300) + self._words(30, 450, 700)
        self.assertEqual(converter._pdfplumber_column_mid(800, words), 400)

    def test_single_column_returns_none(self):
        # 본문이 중앙을 가로지르는 일반 단일 컬럼
        words = self._words(60, 100, 700)
        self.assertIsNone(converter._pdfplumber_column_mid(800, words))

    def test_few_words_returns_none(self):
        words = self._words(10, 50, 300) + self._words(10, 450, 700)
        self.assertIsNone(converter._pdfplumber_column_mid(800, words))

    def test_unbalanced_columns_returns_none(self):
        words = self._words(50, 50, 300) + self._words(5, 450, 700)
        self.assertIsNone(converter._pdfplumber_column_mid(800, words))


def make_paged_table_section_xml(cols=2, table_width=41954, page_width=59528, margin=7087):
    cell_w = table_width // cols
    tcs = ''.join(
        f'<hp:tc><hp:subList><hp:p/></hp:subList>'
        f'<hp:cellAddr colAddr="{c}" rowAddr="0"/>'
        f'<hp:cellSpan colSpan="1" rowSpan="1"/>'
        f'<hp:cellSz width="{cell_w}" height="900"/></hp:tc>'
        for c in range(cols)
    )
    return (
        '<hp:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">'
        f'<hp:pagePr landscape="WIDELY" width="{page_width}" height="84186">'
        f'<hp:margin header="2835" footer="2835" gutter="0" left="{margin}" '
        f'right="{margin}" top="7087" bottom="5669"/></hp:pagePr>'
        f'<hp:tbl rowCnt="1" colCnt="{cols}">'
        f'<hp:sz width="{table_width}" height="900"/>'
        f'<hp:tr>{tcs}</hp:tr></hp:tbl></hp:sec>'
    )


class TableTextWidthTests(unittest.TestCase):
    def test_table_expands_to_text_width(self):
        """규칙 8-1: 표 폭이 본문 폭(페이지 - 좌우 여백)으로 확장된다."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'test.hwpx'
            make_hwpx_with_section(path, make_paged_table_section_xml())
            converter.apply_table_layout_profiles(path, [{'header': ['구분', '내용'], 'rows': [['a', 'b']]}])
            root = read_section(path)
        text_width = 59528 - 7087 * 2  # 45354
        widths = [
            int(sz.get('width')) for sz in root.iter(f'{{{HP_NS}}}cellSz')
        ]
        self.assertEqual(sum(widths), text_width)
        tbl_sz = root.find(f'.//{{{HP_NS}}}tbl/{{{HP_NS}}}sz')
        self.assertEqual(int(tbl_sz.get('width')), text_width)


class OfficialPostProcessTests(unittest.TestCase):
    def test_page_margins_rewritten(self):
        section = (
            '<hp:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">'
            '<hp:pagePr landscape="WIDELY" width="59528" height="84186">'
            '<hp:margin header="4252" footer="4252" gutter="0" left="8504" '
            'right="8504" top="5668" bottom="4252"/></hp:pagePr></hp:sec>'
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'test.hwpx'
            make_hwpx_with_section(path, section)
            converter.apply_official_page_margins(path)
            root = read_section(path)
        margin = root.find(f'{{{HP_NS}}}pagePr/{{{HP_NS}}}margin')
        self.assertEqual(margin.get('top'), '7087')
        self.assertEqual(margin.get('bottom'), '5669')
        self.assertEqual(margin.get('left'), '7087')
        self.assertEqual(margin.get('right'), '7087')
        self.assertEqual(margin.get('header'), '2835')
        self.assertEqual(margin.get('footer'), '2835')


class ComCallRetryTests(unittest.TestCase):
    def test_succeeds_on_first_try(self):
        result = converter._com_call(lambda: 'ok', retries=3, delay=0.0)
        self.assertEqual(result, 'ok')

    def test_retries_until_success(self):
        class FakeComError(Exception):
            pass

        call_count = [0]

        def flaky():
            call_count[0] += 1
            if call_count[0] < 3:
                raise FakeComError('transient')
            return 'recovered'

        with patch.object(converter, '_COM_ERROR', FakeComError):
            result = converter._com_call(flaky, retries=3, delay=0.0)

        self.assertEqual(result, 'recovered')
        self.assertEqual(call_count[0], 3)

    def test_raises_after_exhausting_retries(self):
        class FakeComError(Exception):
            pass

        def always_fails():
            raise FakeComError('persistent')

        with patch.object(converter, '_COM_ERROR', FakeComError):
            with self.assertRaises(FakeComError):
                converter._com_call(always_fails, retries=3, delay=0.0)

    def test_no_retry_when_com_error_is_none(self):
        call_count = [0]

        def fn():
            call_count[0] += 1
            return 'direct'

        with patch.object(converter, '_COM_ERROR', None):
            result = converter._com_call(fn, retries=3, delay=0.0)

        self.assertEqual(result, 'direct')
        self.assertEqual(call_count[0], 1)


class OcrPathTests(unittest.TestCase):
    def test_resolve_kordoc_dir_uses_explicit_path_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            resolved = converter.resolve_kordoc_dir(tmp)

        self.assertEqual(resolved, Path(tmp).resolve())

    def test_resolve_kordoc_dir_uses_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"KORDOC_HOME": tmp}, clear=False):
                resolved = converter.resolve_kordoc_dir()

        self.assertEqual(resolved, Path(tmp).resolve())


if __name__ == "__main__":
    unittest.main()
