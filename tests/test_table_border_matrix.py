"""정본 §8-6 표 테두리 매트릭스 계약.

외곽선 SOLID 0.4mm, 내부선 SOLID 0.12mm,
헤더 하단 DOUBLE_SLIM 0.5mm(본문 1행 상단 미러링), 셀 좌우 안여백 510 hwpunit.
셀 위치 판정은 병합 span 범위 기준.
"""

import tempfile
import unittest
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

import anyway_to_hwpx_com as converter

HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HH = "http://www.hancom.co.kr/hwpml/2011/head"
HC = "http://www.hancom.co.kr/hwpml/2011/core"
NS = {"hp": HP, "hh": HH, "hc": HC}

OUTER = ("SOLID", "0.4 mm")
INNER = ("SOLID", "0.12 mm")
HEADER_SEP = ("DOUBLE_SLIM", "0.5 mm")


def make_header_xml():
    return (
        f'<hh:head xmlns:hh="{HH}" xmlns:hc="{HC}">'
        '<hh:refList><hh:borderFills itemCnt="1">'
        '<hh:borderFill id="1" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0"/>'
        "</hh:borderFills></hh:refList></hh:head>"
    )


def make_table_section_xml(rows, cols):
    trs = []
    for r in range(rows):
        cells = "".join(
            f'<hp:tc header="0" hasMargin="0">'
            f'<hp:cellAddr colAddr="{c}" rowAddr="{r}"/>'
            f'<hp:cellSpan colSpan="1" rowSpan="1"/>'
            f'<hp:cellSz width="1000" height="900"/>'
            f"<hp:subList><hp:p/></hp:subList></hp:tc>"
            for c in range(cols)
        )
        trs.append(f"<hp:tr>{cells}</hp:tr>")
    return (
        f'<hp:sec xmlns:hp="{HP}">'
        f'<hp:tbl colCnt="{cols}" rowCnt="{rows}"><hp:sz width="9000" height="1800"/>'
        f'{"".join(trs)}</hp:tbl></hp:sec>'
    )


def make_layout(rows, cols, merged_cells=None):
    return {
        "header": [f"h{c}" for c in range(cols)],
        "rows": [[f"r{r}c{c}" for c in range(cols)] for r in range(rows - 1)],
        "merged_cells": merged_cells or [],
    }


def apply_and_read(rows, cols, merged_cells=None):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.hwpx"
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("Contents/header.xml", make_header_xml().encode("utf-8"))
            zf.writestr("Contents/section0.xml", make_table_section_xml(rows, cols).encode("utf-8"))

        converter.apply_table_layout_profiles(path, [make_layout(rows, cols, merged_cells)])

        with zipfile.ZipFile(path, "r") as zf:
            header_root = ET.fromstring(zf.read("Contents/header.xml"))
            section_root = ET.fromstring(zf.read("Contents/section0.xml"))
    return header_root, section_root


def cell(section_root, row, col):
    for tc in section_root.findall(".//hp:tc", NS):
        addr = tc.find("hp:cellAddr", NS)
        if addr is not None and addr.get("rowAddr") == str(row) and addr.get("colAddr") == str(col):
            return tc
    raise AssertionError(f"cell ({row},{col}) not found")


def cell_border_fill(header_root, section_root, row, col):
    ref = cell(section_root, row, col).get("borderFillIDRef")
    border_fill = header_root.find(f'.//hh:borderFill[@id="{ref}"]', NS)
    if border_fill is None:
        raise AssertionError(f"borderFill id={ref} for cell ({row},{col}) not found")
    return border_fill


def side(border_fill, name):
    element = border_fill.find(f"hh:{name}Border", NS)
    if element is None:
        raise AssertionError(f"{name}Border missing")
    return (element.get("type"), element.get("width"))


def fill_color(border_fill):
    brush = border_fill.find("hc:fillBrush/hc:winBrush", NS)
    return brush.get("faceColor") if brush is not None else None


class BorderMatrixTests(unittest.TestCase):
    """4행(헤더+본문3) × 3열 — 모든 위치 밴드가 존재하는 기준 격자."""

    @classmethod
    def setUpClass(cls):
        cls.header_root, cls.section_root = apply_and_read(rows=4, cols=3)

    def bf(self, row, col):
        return cell_border_fill(self.header_root, self.section_root, row, col)

    def test_header_left_corner_cell(self):
        bf = self.bf(0, 0)
        self.assertEqual(side(bf, "left"), OUTER)
        self.assertEqual(side(bf, "top"), OUTER)
        self.assertEqual(side(bf, "right"), INNER)
        self.assertEqual(side(bf, "bottom"), HEADER_SEP)
        self.assertEqual(fill_color(bf), "#C8C8C8")

    def test_header_double_line_mirrored_on_body_first_row(self):
        self.assertEqual(side(self.bf(0, 1), "bottom"), HEADER_SEP)
        self.assertEqual(side(self.bf(1, 1), "top"), HEADER_SEP)

    def test_body_center_cell_all_inner_without_fill(self):
        bf = self.bf(2, 1)
        for name in ("left", "right", "top", "bottom"):
            self.assertEqual(side(bf, name), INNER)
        self.assertIsNone(fill_color(bf))

    def test_bottom_right_corner_cell(self):
        bf = self.bf(3, 2)
        self.assertEqual(side(bf, "right"), OUTER)
        self.assertEqual(side(bf, "bottom"), OUTER)
        self.assertEqual(side(bf, "left"), INNER)
        self.assertEqual(side(bf, "top"), INNER)
        self.assertIsNone(fill_color(bf))

    def test_cell_margin_left_right_expanded(self):
        margin = cell(self.section_root, 1, 1).find("hp:cellMargin", NS)
        self.assertIsNotNone(margin)
        self.assertEqual(margin.get("left"), "510")
        self.assertEqual(margin.get("right"), "510")


class BorderMatrixEdgeCaseTests(unittest.TestCase):
    def test_single_row_table_bottom_is_outer_not_double(self):
        header_root, section_root = apply_and_read(rows=1, cols=3)
        bf = cell_border_fill(header_root, section_root, 0, 1)
        self.assertEqual(side(bf, "top"), OUTER)
        self.assertEqual(side(bf, "bottom"), OUTER)
        self.assertEqual(fill_color(bf), "#C8C8C8")

    def test_single_column_table_left_right_both_outer(self):
        header_root, section_root = apply_and_read(rows=3, cols=1)
        bf = cell_border_fill(header_root, section_root, 1, 0)
        self.assertEqual(side(bf, "left"), OUTER)
        self.assertEqual(side(bf, "right"), OUTER)

    def test_merged_cell_touching_right_edge_gets_outer_right(self):
        # 본문 1행 (1,1)이 (1,2)를 흡수 → span 범위가 우측 외곽에 닿음
        header_root, section_root = apply_and_read(rows=4, cols=3, merged_cells=[[1, 1, 1, 2]])
        bf = cell_border_fill(header_root, section_root, 1, 1)
        self.assertEqual(side(bf, "right"), OUTER)
        self.assertEqual(side(bf, "left"), INNER)
        self.assertEqual(side(bf, "top"), HEADER_SEP)

    def test_merged_cell_spanning_to_last_row_gets_outer_bottom(self):
        # 본문 (2,0)이 (3,0)을 흡수 → span 하단이 표 외곽에 닿음
        header_root, section_root = apply_and_read(rows=4, cols=3, merged_cells=[[2, 0, 2, 1]])
        bf = cell_border_fill(header_root, section_root, 2, 0)
        self.assertEqual(side(bf, "bottom"), OUTER)
        self.assertEqual(side(bf, "top"), INNER)


if __name__ == "__main__":
    unittest.main()
