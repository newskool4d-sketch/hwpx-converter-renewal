from __future__ import annotations

from dataclasses import dataclass
from typing import Final
import re
import xml.etree.ElementTree as ET


HH_NS: Final = "http://www.hancom.co.kr/hwpml/2011/head"
HC_NS: Final = "http://www.hancom.co.kr/hwpml/2011/core"
HP_NS: Final = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HS_NS: Final = "http://www.hancom.co.kr/hwpml/2011/section"
XML_NS: Final = {"hh": HH_NS, "hc": HC_NS}

# 정품 한컴이 header.xml·section0.xml 루트에 항상 선언하는 15종.
# python-hwpx 6.0.2 의 HWPML_COMPAT_ROOT_NAMESPACES 와 동일하며,
# 하나라도 빠지면 편집기 안전성 게이트가 호환성 error 로 검출한다.
HWPML_ROOT_NAMESPACES: Final[dict[str, str]] = {
    "ha": "http://www.hancom.co.kr/hwpml/2011/app",
    "hp": HP_NS,
    "hp10": "http://www.hancom.co.kr/hwpml/2016/paragraph",
    "hs": HS_NS,
    "hc": HC_NS,
    "hh": HH_NS,
    "hhs": "http://www.hancom.co.kr/hwpml/2011/history",
    "hm": "http://www.hancom.co.kr/hwpml/2011/master-page",
    "hpf": "http://www.hancom.co.kr/schema/2011/hpf",
    "dc": "http://purl.org/dc/elements/1.1/",
    "opf": "http://www.idpf.org/2007/opf/",
    "ooxmlchart": "http://www.hancom.co.kr/hwpml/2016/ooxmlchart",
    "hwpunitchar": "http://www.hancom.co.kr/hwpml/2016/HwpUnitChar",
    "epub": "http://www.idpf.org/2007/ops",
    "config": "urn:oasis:names:tc:opendocument:xmlns:config:1.0",
}
_XML_DECLARATION: Final = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n'
_ROOT_TAG_NAME_RE: Final = re.compile(r"<[^\s/>]+")
TABLE_BORDER_WIDTH: Final = "0.12 mm"
DIAGONAL_BORDER_WIDTH: Final = "0.1 mm"
TABLE_BORDER_COLOR: Final = "#000000"
BORDER_NAMES: Final = ("leftBorder", "rightBorder", "topBorder", "bottomBorder")

# 정본 §8-6: 외곽 SOLID 0.4mm / 내부 SOLID 0.12mm / 헤더 하단 DOUBLE_SLIM 0.5mm
BorderSide = tuple[str, str]
INNER_SIDE: Final[BorderSide] = ("SOLID", TABLE_BORDER_WIDTH)
OUTER_SIDE: Final[BorderSide] = ("SOLID", "0.4 mm")
HEADER_SEP_SIDE: Final[BorderSide] = ("DOUBLE_SLIM", "0.5 mm")


@dataclass(frozen=True, slots=True)
class BorderFillResult:
    border_id: str
    changed: bool


@dataclass(frozen=True, slots=True)
class CellBorderSpec:
    left: BorderSide = INNER_SIDE
    right: BorderSide = INNER_SIDE
    top: BorderSide = INNER_SIDE
    bottom: BorderSide = INNER_SIDE
    fill_color: str | None = None


def register_hwpx_namespaces() -> None:
    ET.register_namespace("hp", HP_NS)
    ET.register_namespace("hh", HH_NS)
    ET.register_namespace("hc", HC_NS)
    ET.register_namespace("hs", HS_NS)


def serialize_hwpml_part(root: ET.Element) -> bytes:
    """header.xml·section0.xml 을 정품 한컴과 동일한 선언부로 직렬화한다.

    ET 는 실제 사용된 프리픽스만 방출하고 XML 선언에 standalone 을 넣지 않으므로,
    후처리로 파트를 다시 쓰면 COM 이 저장한 정품 선언부가 소실된다.
    이미 선언된 프리픽스는 건드리지 않는다 — 중복 선언은 XML 파싱 자체를 깨뜨린다.
    미등록 네임스페이스에 ET 가 붙이는 ns0: 자동 프리픽스도 함께 차단한다.
    """
    for prefix, uri in HWPML_ROOT_NAMESPACES.items():
        ET.register_namespace(prefix, uri)
    body = ET.tostring(root, encoding="unicode")
    open_tag = body[: body.index(">")]
    insert_at = _ROOT_TAG_NAME_RE.match(body).end()
    missing = "".join(
        f' xmlns:{prefix}="{uri}"'
        for prefix, uri in HWPML_ROOT_NAMESPACES.items()
        if f'xmlns:{prefix}="' not in open_tag
    )
    return (_XML_DECLARATION + body[:insert_at] + missing + body[insert_at:]).encode("utf-8")


def _rgb_color(value: int) -> str:
    return f"#{value & 0xFFFFFF:06X}"


def positional_border_spec(
    row: int,
    col: int,
    row_span: int,
    col_span: int,
    row_count: int,
    col_count: int,
    header_fill_color: int | None = None,
) -> CellBorderSpec:
    """셀 위치(병합 span 범위 기준)에 따른 정본 §8-6 테두리 스펙.

    외곽 접촉이 헤더 경계 이중선보다 우선한다 — 1행 표의 하단은 외곽선.
    이중선은 헤더 하단과 본문 1행 상단 양쪽에 선언해 렌더링을 일관시킨다.
    """
    touches_top = row == 0
    touches_bottom = row + row_span >= row_count
    top = OUTER_SIDE if touches_top else (HEADER_SEP_SIDE if row == 1 else INNER_SIDE)
    bottom = OUTER_SIDE if touches_bottom else (HEADER_SEP_SIDE if row + row_span == 1 else INNER_SIDE)
    return CellBorderSpec(
        left=OUTER_SIDE if col == 0 else INNER_SIDE,
        right=OUTER_SIDE if col + col_span >= col_count else INNER_SIDE,
        top=top,
        bottom=bottom,
        fill_color=_rgb_color(header_fill_color) if row == 0 and header_fill_color is not None else None,
    )


def _spec_sides(spec: CellBorderSpec) -> dict[str, BorderSide]:
    return {
        "leftBorder": spec.left,
        "rightBorder": spec.right,
        "topBorder": spec.top,
        "bottomBorder": spec.bottom,
    }


def _border_fill_count(border_fills: ET.Element) -> int:
    return len(border_fills.findall("hh:borderFill", XML_NS))


def _next_border_fill_id(border_fills: ET.Element) -> str:
    ids: list[int] = []
    for border_fill in border_fills.findall("hh:borderFill", XML_NS):
        raw_id = border_fill.attrib.get("id")
        if raw_id is None:
            continue
        try:
            ids.append(int(raw_id))
        except ValueError:
            continue
    return str(max(ids, default=0) + 1)


def _set_border_fill_count(border_fills: ET.Element) -> None:
    border_fills.set("itemCnt", str(_border_fill_count(border_fills)))


def _border_fill_matches(border_fill: ET.Element, spec: CellBorderSpec) -> bool:
    for border_name, (line_type, line_width) in _spec_sides(spec).items():
        border = border_fill.find(f"hh:{border_name}", XML_NS)
        if border is None:
            return False
        if border.attrib.get("type") != line_type:
            return False
        if border.attrib.get("width") != line_width:
            return False
        if border.attrib.get("color") != TABLE_BORDER_COLOR:
            return False
    win_brush = border_fill.find("hc:fillBrush/hc:winBrush", XML_NS)
    if spec.fill_color is None:
        return win_brush is None
    return win_brush is not None and win_brush.attrib.get("faceColor") == spec.fill_color


def _make_border_fill(spec: CellBorderSpec) -> ET.Element:
    border_fill = ET.Element(
        f"{{{HH_NS}}}borderFill",
        {"threeD": "0", "shadow": "0", "centerLine": "NONE", "breakCellSeparateLine": "0"},
    )
    ET.SubElement(border_fill, f"{{{HH_NS}}}slash", {"type": "NONE", "Crooked": "0", "isCounter": "0"})
    ET.SubElement(border_fill, f"{{{HH_NS}}}backSlash", {"type": "NONE", "Crooked": "0", "isCounter": "0"})
    for border_name, (line_type, line_width) in _spec_sides(spec).items():
        ET.SubElement(
            border_fill,
            f"{{{HH_NS}}}{border_name}",
            {"type": line_type, "width": line_width, "color": TABLE_BORDER_COLOR},
        )
    ET.SubElement(
        border_fill,
        f"{{{HH_NS}}}diagonal",
        {"type": "SOLID", "width": DIAGONAL_BORDER_WIDTH, "color": TABLE_BORDER_COLOR},
    )
    if spec.fill_color is not None:
        fill_brush = ET.SubElement(border_fill, f"{{{HC_NS}}}fillBrush")
        ET.SubElement(fill_brush, f"{{{HC_NS}}}winBrush", {"faceColor": spec.fill_color, "hatchColor": "#999999", "alpha": "0"})
    return border_fill


def _ensure_border_fill(border_fills: ET.Element, spec: CellBorderSpec) -> BorderFillResult:
    for border_fill in border_fills.findall("hh:borderFill", XML_NS):
        border_id = border_fill.attrib.get("id")
        if border_id is not None and _border_fill_matches(border_fill, spec):
            return BorderFillResult(border_id=border_id, changed=False)
    border_id = _next_border_fill_id(border_fills)
    border_fill = _make_border_fill(spec)
    border_fill.set("id", border_id)
    border_fills.append(border_fill)
    _set_border_fill_count(border_fills)
    return BorderFillResult(border_id=border_id, changed=True)


def ensure_cell_border_fill(header_root: ET.Element, spec: CellBorderSpec) -> BorderFillResult:
    border_fills = header_root.find(".//hh:borderFills", XML_NS)
    if border_fills is None:
        raise ValueError("header.xml borderFills not found")
    return _ensure_border_fill(border_fills, spec)
