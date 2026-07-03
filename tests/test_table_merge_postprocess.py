import tempfile
import unittest
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

import anyway_to_hwpx_com as converter
import table_hwpx_postprocess as tpp

HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HH = "http://www.hancom.co.kr/hwpml/2011/head"
HC = "http://www.hancom.co.kr/hwpml/2011/core"
NS = {"hp": HP, "hh": HH, "hc": HC}


def make_header_xml():
    return (
        f'<hh:head xmlns:hh="{HH}" xmlns:hc="{HC}">'
        '<hh:refList><hh:borderFills itemCnt="1">'
        '<hh:borderFill id="1" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0"/>'
        "</hh:borderFills></hh:refList></hh:head>"
    )


def make_table_with_rows(rows=2, cols=3):
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


def write_hwpx(path, section_xml):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("Contents/header.xml", make_header_xml().encode("utf-8"))
        zf.writestr("Contents/section0.xml", section_xml.encode("utf-8"))


class ModularMergeRemovesCoveredCellsTests(unittest.TestCase):
    def test_colspan_merge_removes_covered_cell(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.hwpx"
            write_hwpx(path, make_table_with_rows(rows=2, cols=3))
            layout = {
                "header": ["구분", "", "예산액"],
                "rows": [["강사료", "산출내역", "400,000원"]],
                "merged_cells": [[0, 0, 1, 2]],  # (0,0) 가 (0,1) 흡수
            }

            converter.apply_table_layout_profiles(path, [layout])

            with zipfile.ZipFile(path, "r") as zf:
                root = ET.fromstring(zf.read("Contents/section0.xml"))

        all_tcs = root.findall(".//hp:tc", NS)
        # 6개 중 피병합 (0,1) 1개 제거 → 5개
        self.assertEqual(len(all_tcs), 5)
        # 첫 행은 anchor(0,0)+(0,2) 2개만 남는다
        first_row = root.findall(".//hp:tr", NS)[0]
        self.assertEqual(len(first_row.findall("hp:tc", NS)), 2)
        anchor_span = first_row.find("hp:tc/hp:cellSpan", NS)
        self.assertEqual(anchor_span.get("colSpan"), "2")

    def test_rowspan_merge_removes_covered_cell(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.hwpx"
            write_hwpx(path, make_table_with_rows(rows=2, cols=3))
            layout = {
                "header": ["구분", "내용", "비고"],
                "rows": [["A", "B", "C"]],
                "merged_cells": [[0, 0, 2, 1]],  # (0,0) 가 (1,0) 흡수
            }

            converter.apply_table_layout_profiles(path, [layout])

            with zipfile.ZipFile(path, "r") as zf:
                root = ET.fromstring(zf.read("Contents/section0.xml"))

        self.assertEqual(len(root.findall(".//hp:tc", NS)), 5)
        second_row = root.findall(".//hp:tr", NS)[1]
        self.assertEqual(len(second_row.findall("hp:tc", NS)), 2)
        anchor_span = root.findall(".//hp:tr", NS)[0].find("hp:tc/hp:cellSpan", NS)
        self.assertEqual(anchor_span.get("rowSpan"), "2")

    def test_no_merges_leaves_all_cells(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.hwpx"
            write_hwpx(path, make_table_with_rows(rows=2, cols=3))
            layout = {"header": ["a", "b", "c"], "rows": [["1", "2", "3"]], "merged_cells": []}

            converter.apply_table_layout_profiles(path, [layout])

            with zipfile.ZipFile(path, "r") as zf:
                root = ET.fromstring(zf.read("Contents/section0.xml"))

        self.assertEqual(len(root.findall(".//hp:tc", NS)), 6)


class FilterSpansToGridTests(unittest.TestCase):
    def test_valid_span_kept(self):
        spans = {(0, 0): [0, 0, 1, 2]}
        valid, dropped = tpp._filter_spans_to_grid(spans, col_count=3, row_count=2)
        self.assertEqual(valid, spans)
        self.assertEqual(dropped, [])

    def test_colspan_overflow_dropped(self):
        spans = {(0, 0): [0, 0, 1, 5]}
        valid, dropped = tpp._filter_spans_to_grid(spans, col_count=3, row_count=2)
        self.assertEqual(valid, {})
        self.assertEqual(dropped, [[0, 0, 1, 5]])

    def test_rowspan_overflow_dropped(self):
        spans = {(0, 0): [0, 0, 5, 1]}
        valid, dropped = tpp._filter_spans_to_grid(spans, col_count=3, row_count=2)
        self.assertEqual(valid, {})

    def test_negative_or_zero_span_dropped(self):
        spans = {(0, 0): [0, 0, 0, 1], (1, 1): [-1, 0, 1, 1]}
        valid, dropped = tpp._filter_spans_to_grid(spans, col_count=3, row_count=2)
        self.assertEqual(valid, {})


class OutOfRangeMergeGuardTests(unittest.TestCase):
    def _apply(self, layout):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.hwpx"
            write_hwpx(path, make_table_with_rows(rows=2, cols=3))
            converter.apply_table_layout_profiles(path, [layout])
            with zipfile.ZipFile(path, "r") as zf:
                return ET.fromstring(zf.read("Contents/section0.xml"))

    def test_colspan_overflow_ignored(self):
        layout = {"header": ["a", "b", "c"], "rows": [["1", "2", "3"]], "merged_cells": [[0, 0, 1, 5]]}
        root = self._apply(layout)
        # 범위 초과 병합은 무시 → 6칸 모두 유지, colSpan 오염 없음
        self.assertEqual(len(root.findall(".//hp:tc", NS)), 6)
        anchor_span = root.findall(".//hp:tr", NS)[0].find("hp:tc/hp:cellSpan", NS)
        self.assertEqual(anchor_span.get("colSpan"), "1")

    def test_rowspan_overflow_ignored(self):
        layout = {"header": ["a", "b", "c"], "rows": [["1", "2", "3"]], "merged_cells": [[0, 0, 5, 1]]}
        root = self._apply(layout)
        self.assertEqual(len(root.findall(".//hp:tc", NS)), 6)
        anchor_span = root.findall(".//hp:tr", NS)[0].find("hp:tc/hp:cellSpan", NS)
        self.assertEqual(anchor_span.get("rowSpan"), "1")

    def test_valid_merge_still_works(self):
        layout = {"header": ["구분", "", "예산액"], "rows": [["강사료", "산출", "400원"]], "merged_cells": [[0, 0, 1, 2]]}
        root = self._apply(layout)
        self.assertEqual(len(root.findall(".//hp:tc", NS)), 5)


if __name__ == "__main__":
    unittest.main()
