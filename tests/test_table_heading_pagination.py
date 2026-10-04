"""제목과 표 사이의 문단만 묶는 쪽 나눔 후처리 회귀 검사(COM 불필요)."""

import copy
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

import anyway_to_hwpx_com as converter


HH = converter._NS_HH
HP = converter._NS_HP
HC = converter._NS_HC
NS = {"hh": HH, "hp": HP, "hc": HC}


def _paragraph(pid, text="", char_id="0", para_id="0"):
    paragraph = ET.Element(f"{{{HP}}}p", {
        "id": pid, "paraPrIDRef": para_id, "pageBreak": "0", "columnBreak": "0",
    })
    run = ET.SubElement(paragraph, f"{{{HP}}}run", {"charPrIDRef": char_id})
    ET.SubElement(run, f"{{{HP}}}t").text = text
    return paragraph


def _fixture(blank_count=0, heading_char="1"):
    header = ET.fromstring(
        f'<hh:head xmlns:hh="{HH}" xmlns:hc="{HC}"><hh:refList>'
        '<hh:charProperties>'
        '<hh:charPr id="0" height="1300"/>'
        '<hh:charPr id="1" height="1600"/>'
        '<hh:charPr id="2" height="1400"/>'
        '<hh:charPr id="3" height="1300"><hh:bold/></hh:charPr>'
        '</hh:charProperties><hh:paraProperties itemCnt="1">'
        '<hh:paraPr id="0"><hh:heading type="NONE"/>'
        '<hh:breakSetting breakLatinWord="KEEP_WORD" breakNonLatinWord="KEEP_WORD" '
        'widowOrphan="0" keepWithNext="0" keepLines="0" pageBreakBefore="0" lineWrap="BREAK"/>'
        '<hh:margin><hc:prev value="0" unit="HWPUNIT"/>'
        '<hc:next value="0" unit="HWPUNIT"/></hh:margin>'
        '</hh:paraPr></hh:paraProperties></hh:refList></hh:head>'
    )
    section = ET.Element(f"{{{HP}}}sec")
    section.append(_paragraph("title", "검증 표 제목", heading_char))
    for index in range(blank_count):
        section.append(_paragraph(f"blank-{index}", "   "))
    host = _paragraph("table")
    table = ET.SubElement(host.find("hp:run", NS), f"{{{HP}}}tbl", {
        "id": "test-table", "rowCnt": "2", "colCnt": "2", "pageBreak": "CELL", "repeatHeader": "1",
    })
    ET.SubElement(table, f"{{{HP}}}sz", {"width": "10000", "height": "1800"})
    for row_index in range(2):
        row = ET.SubElement(table, f"{{{HP}}}tr")
        for col_index, width in enumerate((3000, 7000)):
            cell = ET.SubElement(row, f"{{{HP}}}tc", {"header": "1" if row_index == 0 else "0", "hasMargin": "1"})
            ET.SubElement(cell, f"{{{HP}}}cellSz", {"width": str(width), "height": "900"})
            ET.SubElement(cell, f"{{{HP}}}cellMargin", {"left": "510", "right": "510", "top": "200", "bottom": "200"})
            cell.append(_paragraph(f"cell-{row_index}-{col_index}", "머리글" if row_index == 0 else "본문 셀"))
    section.append(host)
    section.append(_paragraph("body", "공유 스타일을 사용하는 본문"))
    return header, section


def _p(section, pid):
    return section.find(f'.//hp:p[@id="{pid}"]', NS)


def _style(header, paragraph):
    return header.find(f'.//hh:paraPr[@id="{paragraph.get("paraPrIDRef")}"]', NS)


def _breaks(header, paragraph):
    return _style(header, paragraph).find("hh:breakSetting", NS)


def _give_page_break_style(header, paragraph):
    container = header.find(".//hh:paraProperties", NS)
    style = copy.deepcopy(_style(header, paragraph))
    style.set("id", "7")
    style.find("hh:breakSetting", NS).set("pageBreakBefore", "1")
    container.append(style)
    container.set("itemCnt", str(len(container)))
    paragraph.set("paraPrIDRef", "7")


class TableHeadingPaginationTests(unittest.TestCase):
    def assert_kept(self, header, paragraph):
        setting = _breaks(header, paragraph)
        self.assertEqual(setting.get("keepWithNext"), "1")
        self.assertEqual(setting.get("keepLines"), "1")

    def test_heading_levels_and_intervening_blanks_are_kept_without_touching_shared_users(self):
        for heading_char in ("1", "2", "3"):
            for blank_count in (0, 3):
                with self.subTest(heading_char=heading_char, blank_count=blank_count):
                    header, section = _fixture(blank_count, heading_char)
                    original_style = ET.tostring(_style(header, _p(section, "body")))
                    host_before = ET.tostring(_p(section, "table"))
                    body_before = ET.tostring(_p(section, "body"))
                    self.assertTrue(converter._keep_table_headings_with_next(header, section))
                    for pid in ["title", *[f"blank-{i}" for i in range(blank_count)]]:
                        self.assert_kept(header, _p(section, pid))
                        self.assertNotEqual(_p(section, pid).get("paraPrIDRef"), "0")
                    self.assertEqual(ET.tostring(_style(header, _p(section, "body"))), original_style)
                    self.assertEqual(ET.tostring(_p(section, "body")), body_before)
                    # 표 호스트·표 안 문단·쪽 나눔·머리글 반복·폭·셀 여백 모두 보존한다.
                    self.assertEqual(ET.tostring(_p(section, "table")), host_before)

    def test_body_between_heading_and_table_does_not_create_a_keep_chain(self):
        header, section = _fixture(2)
        section.insert(1, _paragraph("intervening", "표 앞의 설명 본문"))
        before = (ET.tostring(header), ET.tostring(section))
        self.assertFalse(converter._keep_table_headings_with_next(header, section))
        self.assertEqual((ET.tostring(header), ET.tostring(section)), before)

    def test_normal_body_is_not_treated_as_a_heading(self):
        header, section = _fixture(2, heading_char="0")
        self.assertFalse(converter._keep_table_headings_with_next(header, section))
        self.assertEqual(_p(section, "title").get("paraPrIDRef"), "0")

    def test_picture_or_control_paragraph_is_not_skipped_as_blank(self):
        for tag in ("pic", "ctrl"):
            with self.subTest(tag=tag):
                header, section = _fixture(1)
                obstruction = _paragraph("object")
                ET.SubElement(obstruction.find("hp:run", NS), f"{{{HP}}}{tag}")
                section.insert(1, obstruction)
                before = (ET.tostring(header), ET.tostring(section))
                self.assertFalse(converter._keep_table_headings_with_next(header, section))
                self.assertEqual((ET.tostring(header), ET.tostring(section)), before)

    def test_other_table_is_a_boundary_not_a_blank_paragraph(self):
        header, section = _fixture()
        second_host = copy.deepcopy(_p(section, "table"))
        second_host.set("id", "second-table")
        section.insert(2, _paragraph("between-tables"))
        section.insert(3, second_host)
        first_host_before = ET.tostring(_p(section, "table"))
        second_host_before = ET.tostring(second_host)
        self.assertTrue(converter._keep_table_headings_with_next(header, section))
        self.assert_kept(header, _p(section, "title"))
        self.assertEqual(_p(section, "between-tables").get("paraPrIDRef"), "0")
        self.assertEqual(ET.tostring(_p(section, "table")), first_host_before)
        self.assertEqual(ET.tostring(second_host), second_host_before)

    def test_explicit_page_or_column_break_between_heading_and_table_is_respected(self):
        for attr in ("pageBreak", "columnBreak"):
            for pid in ("blank-0", "table"):
                with self.subTest(attr=attr, pid=pid):
                    header, section = _fixture(2)
                    _p(section, pid).set(attr, "1")
                    before = (ET.tostring(header), ET.tostring(section))
                    self.assertFalse(converter._keep_table_headings_with_next(header, section))
                    self.assertEqual((ET.tostring(header), ET.tostring(section)), before)

    def test_style_page_break_before_between_heading_and_table_is_respected(self):
        for pid in ("blank-0", "table"):
            with self.subTest(pid=pid):
                header, section = _fixture(2)
                _give_page_break_style(header, _p(section, pid))
                before = (ET.tostring(header), ET.tostring(section))
                self.assertFalse(converter._keep_table_headings_with_next(header, section))
                self.assertEqual((ET.tostring(header), ET.tostring(section)), before)

    def test_break_before_the_heading_remains_compatible_with_its_following_table(self):
        for kind in ("pageBreak", "columnBreak", "pageBreakBefore"):
            with self.subTest(kind=kind):
                header, section = _fixture(1)
                heading = _p(section, "title")
                if kind == "pageBreakBefore":
                    _give_page_break_style(header, heading)
                else:
                    heading.set(kind, "1")
                self.assertTrue(converter._keep_table_headings_with_next(header, section))
                self.assert_kept(header, heading)
                if kind == "pageBreakBefore":
                    self.assertEqual(_breaks(header, heading).get(kind), "1")
                else:
                    self.assertEqual(heading.get(kind), "1")

    def test_second_application_is_idempotent_with_unique_style_ids_and_count(self):
        header, section = _fixture(3)
        self.assertTrue(converter._keep_table_headings_with_next(header, section))
        first = (ET.tostring(header), ET.tostring(section))
        self.assertFalse(converter._keep_table_headings_with_next(header, section))
        self.assertEqual((ET.tostring(header), ET.tostring(section)), first)
        container = header.find(".//hh:paraProperties", NS)
        ids = [style.get("id") for style in container.findall("hh:paraPr", NS)]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(int(container.get("itemCnt")), len(ids))

    def test_zip_postprocessing_persists_references_and_is_idempotent(self):
        for prefix, uri in NS.items():
            ET.register_namespace(prefix, uri)
        header, section = _fixture(2)
        host_before = ET.tostring(_p(section, "table"))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pagination.hwpx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("Contents/header.xml", ET.tostring(header, encoding="utf-8"))
                archive.writestr("Contents/section0.xml", ET.tostring(section, encoding="utf-8"))
                archive.writestr("untouched.txt", "preserve this entry")
            converter.apply_official_paragraph_spacing(path)
            with zipfile.ZipFile(path) as archive:
                first = {name: archive.read(name) for name in archive.namelist()}
            saved_header = ET.fromstring(first["Contents/header.xml"])
            saved_section = ET.fromstring(first["Contents/section0.xml"])
            for pid in ("title", "blank-0", "blank-1"):
                self.assert_kept(saved_header, _p(saved_section, pid))
            self.assertEqual(_p(saved_section, "body").get("paraPrIDRef"), "0")
            self.assertEqual(ET.tostring(_p(saved_section, "table")), host_before)
            self.assertEqual(first["untouched.txt"], b"preserve this entry")
            converter.apply_official_paragraph_spacing(path)
            with zipfile.ZipFile(path) as archive:
                second = {name: archive.read(name) for name in archive.namelist()}
            self.assertEqual(second, first)


if __name__ == "__main__":
    unittest.main()
