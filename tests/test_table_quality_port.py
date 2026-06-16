import importlib.util
import importlib
import tempfile
import unittest
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

import anyway_to_hwpx_com as converter


HP_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HH_NS = "http://www.hancom.co.kr/hwpml/2011/head"
HC_NS = "http://www.hancom.co.kr/hwpml/2011/core"
NS = {"hp": HP_NS, "hh": HH_NS, "hc": HC_NS}


def make_header_xml():
    return (
        f'<hh:head xmlns:hh="{HH_NS}" xmlns:hc="{HC_NS}">'
        '<hh:refList><hh:borderFills itemCnt="1">'
        '<hh:borderFill id="1" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0"/>'
        "</hh:borderFills></hh:refList></hh:head>"
    )


def make_table_section_xml(col_count=3):
    cells = []
    for row in range(2):
        for col in range(col_count):
            cells.append(
                f'<hp:tc header="0" hasMargin="0">'
                f'<hp:cellAddr colAddr="{col}" rowAddr="{row}"/>'
                f'<hp:cellSpan colSpan="1" rowSpan="1"/>'
                f'<hp:cellSz width="1" height="900"/>'
                f'<hp:subList><hp:p/></hp:subList>'
                f"</hp:tc>"
            )
    return (
        f'<hp:sec xmlns:hp="{HP_NS}">'
        f'<hp:tbl colCnt="{col_count}" rowCnt="2">'
        f'<hp:sz width="9000" height="1800"/>'
        f'{"".join(cells)}</hp:tbl></hp:sec>'
    )


def write_hwpx(path, section_xml):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("Contents/header.xml", make_header_xml().encode("utf-8"))
        zf.writestr("Contents/section0.xml", section_xml.encode("utf-8"))


class TableContractParserTests(unittest.TestCase):
    def test_markdown_table_carries_table_source(self):
        blocks = converter.parse_markdown("| 구분 | 내용 |\n|---|---|\n| A | B |")
        self.assertEqual(blocks[0]["table_source"], "markdown")

    def test_html_table_preserves_cell_spans(self):
        if importlib.util.find_spec("bs4") is None:
            self.skipTest("beautifulsoup4 not installed")
        blocks = converter.parse_html(
            "<table>"
            '<tr><th rowspan="2">구분</th><th colspan="2">내용</th></tr>'
            "<tr><th>세부</th><th>담당</th></tr>"
            "<tr><td>A</td><td>긴 내용</td><td>홍길동</td></tr>"
            "</table>"
        )
        self.assertEqual(
            blocks,
            [
                {
                    "type": "table",
                    "header": ["구분", "내용", ""],
                    "rows": [["", "세부", "담당"], ["A", "긴 내용", "홍길동"]],
                    "table_source": "html",
                    "merged_cells": [[0, 0, 2, 1], [0, 1, 1, 2]],
                }
            ],
        )

    def test_xlsx_table_preserves_sheet_and_merged_cells(self):
        if importlib.util.find_spec("openpyxl") is None:
            self.skipTest("openpyxl not installed")
        Workbook = getattr(importlib.import_module("openpyxl"), "Workbook")

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "merged.xlsx"
            workbook = Workbook()
            worksheet = workbook.active
            worksheet.title = "예산"
            worksheet.merge_cells("A1:B1")
            worksheet["A1"] = "항목"
            worksheet["C1"] = "예산액"
            worksheet.append(["강사료", "산출내역", "400,000원"])
            workbook.save(path)
            workbook.close()

            blocks = converter.parse_xlsx(path)

        self.assertEqual(
            blocks,
            [
                {"type": "h", "level": 2, "text": "예산"},
                {
                    "type": "table",
                    "header": ["항목", "", "예산액"],
                    "rows": [["강사료", "산출내역", "400,000원"]],
                    "table_source": "xlsx",
                    "worksheet_title": "예산",
                    "merged_cells": [[0, 0, 1, 2]],
                },
            ],
        )

    def test_docx_table_preserves_source_and_merged_cells(self):
        if importlib.util.find_spec("docx") is None:
            self.skipTest("python-docx not installed")
        Document = getattr(importlib.import_module("docx"), "Document")

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "merged.docx"
            document = Document()
            table = document.add_table(rows=2, cols=3)
            table.cell(0, 0).merge(table.cell(0, 1))
            table.cell(0, 0).text = "항목"
            table.cell(0, 2).text = "예산액"
            table.cell(1, 0).text = "강사료"
            table.cell(1, 1).text = "산출내역"
            table.cell(1, 2).text = "400,000원"
            document.save(path)

            blocks = converter.parse_docx(path)

        self.assertEqual(blocks[0]["table_source"], "docx")
        self.assertEqual(blocks[0]["header"], ["항목", "", "예산액"])
        self.assertEqual(blocks[0]["merged_cells"], [[0, 0, 1, 2]])

    def test_pdf_odl_table_preserves_source_and_merged_cells(self):
        element = {
            "type": "table",
            "rows": [
                {"cells": [{"rowspan": 2, "kids": [{"type": "paragraph", "content": "구분"}]}, {"colspan": 2, "kids": [{"type": "paragraph", "content": "내용"}]}]},
                {"cells": [{"kids": [{"type": "paragraph", "content": "세부"}]}, {"kids": [{"type": "paragraph", "content": "담당"}]}]},
                {"cells": [{"kids": [{"type": "paragraph", "content": "A"}]}, {"kids": [{"type": "paragraph", "content": "긴 내용"}]}, {"kids": [{"type": "paragraph", "content": "홍길동"}]}]},
            ],
        }

        blocks = converter._odl_element_to_blocks(element)

        self.assertEqual(
            blocks,
            [
                {
                    "type": "table",
                    "header": ["구분", "내용", ""],
                    "rows": [["", "세부", "담당"], ["A", "긴 내용", "홍길동"]],
                    "table_source": "pdf",
                    "merged_cells": [[0, 0, 2, 1], [0, 1, 1, 2]],
                }
            ],
        )


class TableLayoutContractTests(unittest.TestCase):
    def test_budget_role_uses_budget_width_profile(self):
        from table_model import table_layout_for

        layout = table_layout_for(["항목", "산출내역", "예산액"], [["강사료", "2명 x 2시간", "400,000원"]], total_width=10000)

        self.assertEqual(layout.table_role, "budget")
        self.assertEqual(layout.column_widths, [2400, 5000, 2600])


class TableHwpxPostProcessTests(unittest.TestCase):
    def test_postprocess_applies_border_fills_margins_and_cell_span(self):
        with tempfile.TemporaryDirectory() as tmp:
            hwpx_path = Path(tmp) / "table.hwpx"
            write_hwpx(hwpx_path, make_table_section_xml(3))
            layout = {
                "header": ["항목", "", "예산액"],
                "rows": [["강사료", "산출내역", "400,000원"]],
                "column_widths": [2400, 5000, 2600],
                "merged_cells": [[0, 0, 1, 2]],
            }

            converter.apply_table_layout_profiles(hwpx_path, [layout])

            with zipfile.ZipFile(hwpx_path, "r") as zf:
                header_root = ET.fromstring(zf.read("Contents/header.xml"))
                section_root = ET.fromstring(zf.read("Contents/section0.xml"))

        border_fills = header_root.find(".//hh:borderFills", NS)
        header_brush = header_root.find('.//hh:borderFill[@id="3"]/hc:fillBrush/hc:winBrush', NS)
        first_cell = section_root.find(".//hp:tc", NS)
        last_cell = section_root.findall(".//hp:tc", NS)[-1]
        if border_fills is None or header_brush is None or first_cell is None:
            self.fail("expected table border fills and first cell")
        span = first_cell.find("hp:cellSpan", NS)
        margin = first_cell.find("hp:cellMargin", NS)
        if span is None or margin is None:
            self.fail("expected first cell span and margin")

        self.assertEqual(border_fills.get("itemCnt"), "3")
        self.assertEqual(header_brush.get("faceColor"), "#E7E7E7")
        self.assertEqual(first_cell.get("header"), "1")
        self.assertEqual(first_cell.get("borderFillIDRef"), "3")
        self.assertEqual(last_cell.get("borderFillIDRef"), "2")
        self.assertEqual(span.get("colSpan"), "2")
        self.assertEqual(span.get("rowSpan"), "1")
        self.assertEqual(margin.attrib, {"left": "170", "right": "170", "top": "120", "bottom": "120"})


if __name__ == "__main__":
    unittest.main()
