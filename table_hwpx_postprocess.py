from __future__ import annotations

from collections.abc import Mapping, Sequence
import os
import shutil
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET

from hwpx_layout import TABLE_TOTAL_WIDTH
from hwpx_layout import calc_row_heights
from hwpx_layout import calc_table_after_para_space
from hwpx_layout import calc_table_cell_margin
from hwpx_layout import calc_table_cell_para_space
from table_model import TableBlock
from table_model import TableLayout
from table_model import table_layout_from_block
from table_model import table_layout_for
from table_hwpx_styles import HP_NS
from table_hwpx_styles import ensure_table_border_fills
from table_hwpx_styles import register_hwpx_namespaces


NS = {"hp": HP_NS}


def _rewrite_zip_entry(zip_path, entry_name: str, data: bytes) -> None:
    src = os.fspath(zip_path)
    fd, tmp_name = tempfile.mkstemp(suffix=".hwpx")
    os.close(fd)
    try:
        with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(tmp_name, "w") as zout:
            for item in zin.infolist():
                content = data if item.filename == entry_name else zin.read(item.filename)
                zi = zipfile.ZipInfo(item.filename, item.date_time)
                zi.comment = item.comment
                zi.extra = item.extra
                zi.internal_attr = item.internal_attr
                zi.external_attr = item.external_attr
                zi.create_system = item.create_system
                zi.compress_type = item.compress_type
                zout.writestr(zi, content)
        shutil.move(tmp_name, src)
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


def _int_attr(element: ET.Element, name: str, default: int = 0) -> int:
    try:
        return int(element.attrib.get(name, default) or default)
    except (TypeError, ValueError):
        return default


def _set_attrs(element: ET.Element, attrs: Mapping[str, int | str]) -> bool:
    changed = False
    for key, value in attrs.items():
        text = str(value)
        if element.attrib.get(key) != text:
            element.set(key, text)
            changed = True
    return changed


def _hp_tag(name: str) -> str:
    return f"{{{HP_NS}}}{name}"


def _ensure_child(parent: ET.Element, tag_name: str) -> ET.Element:
    child = parent.find(_hp_tag(tag_name))
    if child is None:
        child = ET.SubElement(parent, _hp_tag(tag_name))
    return child


def _section_text_width(root: ET.Element) -> int | None:
    page_pr = root.find(f".//{{{HP_NS}}}pagePr")
    if page_pr is None:
        return None
    page_width = _int_attr(page_pr, "width", 0)
    margin = page_pr.find(f"{{{HP_NS}}}margin")
    if page_width <= 0 or margin is None:
        return None
    width = page_width - _int_attr(margin, "left", 0) - _int_attr(margin, "right", 0) - _int_attr(margin, "gutter", 0)
    return width if width > 1000 else None


def _iter_parent_child_pairs(root: ET.Element):
    for parent in root.iter():
        for child in list(parent):
            yield parent, child


def _compact_paragraph_after_table(root: ET.Element, tbl: ET.Element, attrs: dict[str, int]) -> bool:
    for parent, child in _iter_parent_child_pairs(root):
        if child is not tbl:
            continue
        siblings = list(parent)
        idx = siblings.index(child)
        for next_sibling in siblings[idx + 1:]:
            if next_sibling.tag == _hp_tag("p"):
                para_pr = _ensure_child(next_sibling, "paraPr")
                return _set_attrs(para_pr, attrs)
        return False
    return False


def _compact_cell_paragraphs(tc: ET.Element, attrs: dict[str, int]) -> bool:
    changed = False
    for para in tc.findall(".//hp:p", NS):
        para_pr = _ensure_child(para, "paraPr")
        changed = _set_attrs(para_pr, attrs) or changed
    return changed


def _ensure_cell_margin(tc: ET.Element, layout: TableLayout) -> bool:
    cell_margin = _ensure_child(tc, "cellMargin")
    return _set_attrs(
        cell_margin,
        {
            "left": layout.style.margin_left,
            "right": layout.style.margin_right,
            "top": layout.style.margin_top,
            "bottom": layout.style.margin_bottom,
        },
    )


def _ensure_table_cell_margin(tbl: ET.Element, attrs: dict[str, int]) -> bool:
    cell_margin = _ensure_child(tbl, "cellMargin")
    return _set_attrs(cell_margin, attrs)


def _ensure_cell_span(tc: ET.Element) -> ET.Element:
    return _ensure_child(tc, "cellSpan")


def _span_by_addr(layout: TableLayout) -> dict[tuple[int, int], list[int]]:
    return {(span[0], span[1]): span for span in layout.merged_cells if len(span) == 4}


def _layout_for(layout: TableLayout | TableBlock, total_width: int) -> TableLayout:
    if isinstance(layout, TableLayout):
        return table_layout_for(
            layout.header,
            layout.rows,
            layout.table_role,
            layout.column_widths,
            layout.table_source,
            layout.worksheet_title,
            layout.merged_cells,
            total_width=total_width,
        )
    return table_layout_from_block(layout, total_width=total_width)


def _read_header_root(hwpx_path, header_name: str) -> ET.Element | None:
    try:
        with zipfile.ZipFile(hwpx_path, "r") as zf:
            return ET.fromstring(zf.read(header_name))
    except KeyError:
        return None


def apply_table_layout_profiles(hwpx_path, table_layouts: Sequence[TableLayout | TableBlock]) -> None:
    apply_table_width_profiles(hwpx_path, table_layouts)


def apply_table_width_profiles(hwpx_path, table_layouts: Sequence[TableLayout | TableBlock]) -> None:
    if not table_layouts or not os.path.exists(hwpx_path):
        return
    section_name = "Contents/section0.xml"
    header_name = "Contents/header.xml"
    try:
        with zipfile.ZipFile(hwpx_path, "r") as zf:
            section_xml = zf.read(section_name)
    except (KeyError, OSError, zipfile.BadZipFile) as exc:
        print(f"  [경고] 표 후처리 준비 실패: {exc}", file=sys.stderr)
        return
    try:
        register_hwpx_namespaces()
        root = ET.fromstring(section_xml)
        header_root = _read_header_root(hwpx_path, header_name)
        changed = False
        header_changed = False
        text_width = _section_text_width(root)
        for table_index, tbl in enumerate(root.findall(".//hp:tbl", NS)):
            if table_index >= len(table_layouts):
                break
            col_count = _int_attr(tbl, "colCnt", 0)
            if col_count <= 0:
                continue
            sz = tbl.find("hp:sz", NS)
            total_width = text_width or (int(sz.attrib.get("width", TABLE_TOTAL_WIDTH) or TABLE_TOTAL_WIDTH) if sz is not None else TABLE_TOTAL_WIDTH)
            layout = _layout_for(table_layouts[table_index], total_width)
            widths = layout.column_widths
            if len(widths) != col_count:
                widths = table_layout_for(layout.header, layout.rows, total_width=total_width).column_widths
            row_heights = calc_row_heights(layout.header, layout.rows, widths)
            if sz is not None:
                changed = _set_attrs(sz, {"width": sum(widths), "height": sum(row_heights)}) or changed
            border_refs = ensure_table_border_fills(header_root, layout.style) if header_root is not None else None
            header_changed = header_changed or bool(border_refs and border_refs.changed)
            if border_refs is not None:
                tbl.set("borderFillIDRef", border_refs.body_id)
                changed = True
            spans = _span_by_addr(layout)
            cell_para_space = calc_table_cell_para_space(layout.header, layout.rows, widths)
            after_para_space = calc_table_after_para_space(layout.header, layout.rows, widths)
            changed = _ensure_table_cell_margin(tbl, calc_table_cell_margin(layout.header, layout.rows, widths)) or changed
            for tc in tbl.findall(".//hp:tc", NS):
                cell_addr = tc.find("hp:cellAddr", NS)
                if cell_addr is None:
                    continue
                cell_sz = tc.find("hp:cellSz", NS)
                if cell_sz is None:
                    cell_sz = ET.SubElement(tc, _hp_tag("cellSz"))
                row = _int_attr(cell_addr, "rowAddr", 0)
                col = _int_attr(cell_addr, "colAddr", 0)
                row_span = 1
                col_span = 1
                span = spans.get((row, col))
                if span is not None:
                    row_span = span[2]
                    col_span = span[3]
                    cell_span = _ensure_cell_span(tc)
                    changed = _set_attrs(cell_span, {"rowSpan": row_span, "colSpan": col_span}) or changed
                if 0 <= col < len(widths):
                    changed = _set_attrs(cell_sz, {"width": sum(widths[col : min(len(widths), col + col_span)])}) or changed
                if 0 <= row < len(row_heights):
                    changed = _set_attrs(cell_sz, {"height": sum(row_heights[row : min(len(row_heights), row + row_span)])}) or changed
                if row == 0:
                    tc.set("header", "1")
                    if border_refs is not None:
                        tc.set("borderFillIDRef", border_refs.header_id)
                elif border_refs is not None:
                    tc.set("borderFillIDRef", border_refs.body_id)
                tc.set("hasMargin", "1")
                changed = _ensure_cell_margin(tc, layout) or changed
                changed = _compact_cell_paragraphs(tc, cell_para_space) or changed
            changed = _compact_paragraph_after_table(root, tbl, after_para_space) or changed
        if header_root is not None and header_changed:
            _rewrite_zip_entry(hwpx_path, header_name, ET.tostring(header_root, encoding="utf-8", xml_declaration=True))
        if changed:
            _rewrite_zip_entry(hwpx_path, section_name, ET.tostring(root, encoding="utf-8", xml_declaration=True))
    except (ET.ParseError, OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"  [경고] 표 후처리 실패: {exc}", file=sys.stderr)
