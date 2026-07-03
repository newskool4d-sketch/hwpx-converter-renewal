from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Callable, Sequence
from typing import Final

CellValue = str | int | float | None
Rows = Sequence[Sequence[CellValue]]
Spacing = dict[str, int]

TABLE_TOTAL_WIDTH, TABLE_MIN_ROW_HEIGHT, TABLE_MAX_ROW_HEIGHT = 14000, 900, 7600
TABLE_LINE_HEIGHT, TABLE_CELL_HPAD, TABLE_UNIT_PER_VISUAL = 560, 240, 135
TABLE_CELL_MARGIN: Final[Spacing] = {'left': 120, 'right': 120, 'top': 80, 'bottom': 80}
TABLE_CELL_PARA_SPACE: Final[Spacing] = {'spaceBefore': 0, 'spaceAfter': 0}
TABLE_AFTER_PARA_SPACE: Final[Spacing] = {'spaceBefore': 160, 'spaceAfter': 0}

OFFICIAL_LIST_LEFT_STOPS: Final[tuple[int, ...]] = (0, 360, 720, 1080, 1440, 1800, 2160, 2520, 2880)
OFFICIAL_LIST_BODY_STOPS: Final[tuple[int, ...]] = (620, 900, 1260, 1620, 1980, 2400, 2760, 3060, 3420)
OFFICIAL_LIST_MIN_GAP, OFFICIAL_LIST_HANG_UNIT = 240, 120

OFFICIAL_LIST_PATTERNS: Final[tuple[tuple[int, re.Pattern[str]], ...]] = (
    (0, re.compile(r'^([ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+\.?)[ \t]*(\S.*)$')),
    (1, re.compile(r'^(\d{1,2}\.)(?!\d)[ \t]*(\S.*)$')),
    (2, re.compile(r'^([가나다라마바사아자차카타파하]\.)[ \t]*(\S.*)$')),
    (3, re.compile(r'^(\d{1,2}\))[ \t]*(\S.*)$')),
    (4, re.compile(r'^([가나다라마바사아자차카타파하]\))[ \t]*(\S.*)$')),
    (5, re.compile(r'^(\(\d{1,2}\))[ \t]*(\S.*)$')),
    (6, re.compile(r'^(\([가나다라마바사아자차카타파하]\))[ \t]*(\S.*)$')),
    (7, re.compile(r'^([①②③④⑤⑥⑦⑧⑨⑩])[ \t]*(\S.*)$')),
    (8, re.compile(r'^([㉮㉯㉰㉱㉲㉳㉴㉵㉶㉷])[ \t]*(\S.*)$')),
)
OFFICIAL_LIST_MAX_DEPTH: Final = max(depth for depth, _ in OFFICIAL_LIST_PATTERNS)

TABLE_HEADER_WIDTH_PROFILES: Final[dict[tuple[str, ...], list[int]]] = {
    ('구분', '내용'): [25, 75],
    ('구분', '주요 내용'): [25, 75],
    ('방향', '내용'): [25, 75],
    ('판단 사항', '검토 내용'): [30, 70],
    ('기관·부서', '역할'): [30, 70],
    ('번호', '문항', '유형'): [10, 75, 15],
    ('시간', '내용', '담당'): [20, 60, 20],
    ('단계', '내용', '시기'): [18, 62, 20],
    ('구분', '인원', '역할'): [20, 15, 65],
}
TABLE_DEFAULT_WIDTH_PROFILES: Final[dict[int, list[int]]] = {
    2: [28, 72],
    3: [18, 62, 20],
    4: [15, 35, 25, 25],
}
COLUMN_PROFILES: Final[dict[str, dict[str, float]]] = {
    'index': {'min': 650, 'pref': 850, 'max': 1100, 'weight': 0.3},
    'number': {'min': 900, 'pref': 1300, 'max': 2200, 'weight': 0.6},
    'date': {'min': 1200, 'pref': 1700, 'max': 2600, 'weight': 0.7},
    'name': {'min': 850, 'pref': 1200, 'max': 1900, 'weight': 0.5},
    'position': {'min': 1000, 'pref': 1500, 'max': 2400, 'weight': 0.6},
    'org': {'min': 1500, 'pref': 2500, 'max': 4400, 'weight': 1.0},
    'title': {'min': 1500, 'pref': 2800, 'max': 5600, 'weight': 1.25},
    'detail': {'min': 1900, 'pref': 4300, 'max': 12500, 'weight': 2.6},
    'generic': {'min': 1000, 'pref': 1900, 'max': 4400, 'weight': 1.0},
}

DETAIL_HEADER_PATTERN: Final = re.compile(r'(내용|세부|비고|사유|설명|의견|주소|목적|방법|추진|계획|결과|특이|주요|개요|remark|note|description|detail|comment)', re.IGNORECASE)
ORG_HEADER_PATTERN: Final = re.compile(r'(기관|학교|부서|소속|단체|업체|교육청|지원청|org|organization|department)', re.IGNORECASE)
TITLE_HEADER_PATTERN: Final = re.compile(r'(명칭|제목|사업명|프로그램명|과정명|행사명|title|subject)', re.IGNORECASE)
VALUE_HEADER_PATTERN: Final = re.compile(r'^(값|내용|value)$', re.IGNORECASE)
POSITION_HEADER_PATTERN: Final = re.compile(r'(직위|직급|직책|보직|담당|role|position|rank)', re.IGNORECASE)
NAME_HEADER_PATTERN: Final = re.compile(r'(성명|이름|성함|신청자|담당자|name)', re.IGNORECASE)
DATE_HEADER_PATTERN: Final = re.compile(r'(일자|날짜|기간|시간|시각|연도|월일|date|time|period)', re.IGNORECASE)
NUMBER_HEADER_PATTERN: Final = re.compile(r'(금액|예산|단가|합계|수량|인원|계|원|명|건|회|비율|%|amount|price|total|count|number)', re.IGNORECASE)
INDEX_HEADER_PATTERN: Final = re.compile(r'^(순번|연번|번호|no\.?|#)$', re.IGNORECASE)
NUMBER_VALUE_PATTERN: Final = re.compile(r'^\s*[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\s*(?:원|명|건|회|%|개|점)?\s*$')
DATE_VALUE_PATTERN: Final = re.compile(r'^\s*\d{2,4}[./-]\d{1,2}(?:[./-]\d{1,2})?(?:\s*[-~]\s*\d{1,2}[./-]\d{1,2})?\s*$')


def visual_width(text: CellValue) -> int:
    width = 0
    for char in str(text or ''):
        if unicodedata.combining(char):
            continue
        width += 2 if unicodedata.east_asian_width(char) in ('F', 'W') else 1
    return max(width, 1)


def normalize_table_rows(header: Sequence[CellValue], rows: Rows) -> tuple[list[list[str]], int]:
    all_rows = ([header] if header else []) + list(rows or [])
    col_count = max((len(row) for row in all_rows), default=0)
    normalized = []
    for row in all_rows:
        values = [str(cell or '').strip() for cell in row]
        normalized.append(values + [''] * (col_count - len(values)))
    return normalized, col_count


# 시행문(대외) 항목체계: 정본 §2-1 8단계는 '1.'에서 시작한다.
# 로마숫자(Ⅰ.) depth 0을 제거하고 나머지를 한 단계씩 당긴다.
OFFICIAL_LIST_PATTERNS_NO_ROMAN: Final[tuple[tuple[int, re.Pattern[str]], ...]] = tuple(
    (depth - 1, pattern) for depth, pattern in OFFICIAL_LIST_PATTERNS if depth >= 1
)


def detect_official_list_item(
    line: str,
    clean_inline: Callable[[str], str],
    allow_roman: bool = True,
) -> dict[str, str | int] | None:
    stripped = line.strip()
    patterns = OFFICIAL_LIST_PATTERNS if allow_roman else OFFICIAL_LIST_PATTERNS_NO_ROMAN
    for depth, pattern in patterns:
        match = pattern.match(stripped)
        if match is None:
            continue
        marker = match.group(1)
        content = clean_inline(match.group(2))
        return {'depth': depth, 'text': f'{marker} {content}', 'marker': marker, 'content': content}
    bullet = re.match(r'^[-*]\s+(.*)', stripped)
    if bullet is None:
        return None
    content = clean_inline(bullet.group(1))
    return {'depth': 1, 'text': f'• {content}', 'marker': '•', 'content': content}


def official_list_para_shape(depth: int, marker: str = '') -> dict[str, int]:
    bounded = max(0, min(int(depth or 0), OFFICIAL_LIST_MAX_DEPTH))
    marker_start = OFFICIAL_LIST_LEFT_STOPS[bounded]
    body_start = OFFICIAL_LIST_BODY_STOPS[bounded]
    marker_box = visual_width(marker or '1.') * OFFICIAL_LIST_HANG_UNIT + OFFICIAL_LIST_MIN_GAP
    body_start = max(body_start, marker_start + marker_box)
    return {
        'align': 0,
        'indent_left': body_start,
        'indent_first': marker_start - body_start,
        'text_gap': body_start - marker_start,
        'space_before': 0,
        'space_after': 80 if bounded <= 2 else 40,
    }


def _percentile(values: Sequence[int], ratio: float) -> int:
    if not values:
        return 1
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, math.ceil(len(ordered) * ratio) - 1))
    return ordered[idx]


def _infer_col_kind(header_text: str, values: Sequence[str], col_index: int) -> str:
    body_values = [str(value or '').strip() for value in values if str(value or '').strip()]
    for pattern, kind in (
        (INDEX_HEADER_PATTERN, 'index'), (VALUE_HEADER_PATTERN, 'detail'), (DETAIL_HEADER_PATTERN, 'detail'),
        (ORG_HEADER_PATTERN, 'org'), (TITLE_HEADER_PATTERN, 'title'), (POSITION_HEADER_PATTERN, 'position'),
        (NAME_HEADER_PATTERN, 'name'), (DATE_HEADER_PATTERN, 'date'), (NUMBER_HEADER_PATTERN, 'number'),
    ):
        if pattern.search(header_text):
            return kind
    if not header_text and col_index == 0 and body_values and all(visual_width(value) <= 4 for value in body_values):
        return 'index'
    if not body_values:
        return 'generic'
    numeric_hits = sum(1 for value in body_values if NUMBER_VALUE_PATTERN.match(value))
    date_hits = sum(1 for value in body_values if DATE_VALUE_PATTERN.match(value))
    if numeric_hits / len(body_values) >= 0.75:
        return 'number'
    if date_hits / len(body_values) >= 0.6:
        return 'date'
    widths = [visual_width(value) for value in body_values]
    avg_width = sum(widths) / len(widths)
    if _percentile(widths, 0.9) >= 28 or avg_width >= 18:
        return 'detail'
    if not header_text and avg_width <= 8 and all(' ' not in value for value in body_values[:10]):
        return 'name'
    return 'generic'


def _content_preferred_width(kind: str, header_text: str, values: Sequence[str]) -> int:
    widths = [visual_width(header_text), *[visual_width(value) for value in values if str(value or '').strip()]]
    p90 = _percentile(widths, 0.9)
    longest = max(widths or [1])
    if kind == 'detail':
        visual_units = min(max(longest * 0.85, p90, 18), 90)
    elif kind in ('org', 'title'):
        visual_units = min(max(p90, 12), 38)
    elif kind in ('number', 'date', 'position'):
        visual_units = min(max(longest, 7), 20)
    elif kind == 'index':
        visual_units = min(max(longest, 3), 6)
    else:
        visual_units = min(max(p90, 8), 30)
    return int(visual_units * TABLE_UNIT_PER_VISUAL + TABLE_CELL_HPAD)


def _profile_to_widths(profile: Sequence[int], total: int = TABLE_TOTAL_WIDTH) -> list[int]:
    profile_sum = sum(profile)
    if profile_sum <= 0:
        return []
    widths = [max(1, int(total * value / profile_sum)) for value in profile]
    widths[profile.index(max(profile))] += total - sum(widths)
    return widths


def _table_header_profile(header: Sequence[CellValue], col_count: int) -> list[int] | None:
    normalized_header = tuple(str(cell or '').strip() for cell in (header or []))
    return TABLE_HEADER_WIDTH_PROFILES.get(normalized_header) or TABLE_DEFAULT_WIDTH_PROFILES.get(col_count)


def _redistribute_widths(widths: list[int], kinds: list[str], total: int, target_widths: Sequence[int] | None = None, scale: float = 1.0) -> list[int]:
    profiles = [COLUMN_PROFILES[kind] for kind in kinds]
    p_min = [int(p['min'] * scale) for p in profiles]
    p_max = [int(p['max'] * scale) for p in profiles]
    p_weight = [p['weight'] for p in profiles]
    result = [max(p_min[i], min(p_max[i], widths[i])) for i in range(len(widths))]
    while sum(result) > total:
        shrinkable = [idx for idx in range(len(result)) if result[idx] > p_min[idx]]
        if not shrinkable:
            break
        idx = min(shrinkable, key=lambda item: p_weight[item])
        if result[idx] <= p_min[idx]:
            break
        result[idx] -= 1
    while sum(result) < total and target_widths is not None:
        candidates = [idx for idx in range(len(result)) if result[idx] < min(target_widths[idx], p_max[idx])]
        if not candidates:
            break
        idx = max(candidates, key=lambda item: min(target_widths[item], p_max[item]) - result[item])
        result[idx] += 1
    while sum(result) < total:
        idx = max(range(len(result)), key=lambda item: (p_max[item] - result[item]) * p_weight[item])
        if result[idx] >= p_max[idx]:
            break
        result[idx] += 1
    if sum(result) != total:
        idx = max(range(len(result)), key=lambda item: p_weight[item])
        result[idx] += total - sum(result)
    return result


def calc_col_widths(header: Sequence[CellValue], rows: Rows, total: int = TABLE_TOTAL_WIDTH) -> list[int]:
    normalized, col_count = normalize_table_rows(header or [], rows or [])
    if col_count == 0:
        return []
    if col_count == 1:
        return [total]
    scale = total / TABLE_TOTAL_WIDTH
    profile_widths = _profile_to_widths(_table_header_profile(header or [], col_count) or [1] * col_count, total)
    kinds: list[str] = []
    preferred: list[int] = []
    for col_index in range(col_count):
        header_text = normalized[0][col_index] if header else ''
        values = [row[col_index] for row in normalized[1 if header else 0:]]
        kind = _infer_col_kind(header_text, values, col_index)
        content_width = _content_preferred_width(kind, header_text, values)
        baseline = profile_widths[col_index]
        kinds.append(kind)
        profile_bias = int(baseline * 0.75)
        preferred.append(max(int(COLUMN_PROFILES[kind]['pref'] * scale), profile_bias, content_width))
    return _redistribute_widths(preferred, kinds, total, profile_widths, scale)


def _line_counts(header: Sequence[CellValue], rows: Rows, col_widths: Sequence[int]) -> list[int]:
    normalized, col_count = normalize_table_rows(header or [], rows or [])
    counts: list[int] = []
    for row in normalized:
        max_lines = 1
        for col_index in range(col_count):
            text = row[col_index]
            usable_width = max(300, col_widths[min(col_index, len(col_widths) - 1)] - TABLE_CELL_HPAD)
            capacity = max(2, int(usable_width / TABLE_UNIT_PER_VISUAL))
            parts = str(text or '').splitlines() or ['']
            max_lines = max(max_lines, sum(max(1, math.ceil(visual_width(part) / capacity)) for part in parts))
        counts.append(max_lines)
    return counts


def calc_table_cell_margin(header: Sequence[CellValue], rows: Rows, col_widths: Sequence[int]) -> Spacing:
    lines = _line_counts(header, rows, col_widths) if col_widths else [1]
    avg_lines = sum(lines) / len(lines)
    max_lines = max(lines)
    if max_lines >= 5 or avg_lines >= 2.4:
        return {'left': 90, 'right': 90, 'top': 55, 'bottom': 55}
    if max_lines <= 1 and len(rows) <= 3:
        return {'left': 150, 'right': 150, 'top': 100, 'bottom': 100}
    return dict(TABLE_CELL_MARGIN)


def calc_table_cell_para_space(header: Sequence[CellValue], rows: Rows, col_widths: Sequence[int]) -> Spacing:
    lines = _line_counts(header, rows, col_widths) if col_widths else [1]
    return {'spaceBefore': 0, 'spaceAfter': 0 if max(lines) >= 3 else 20}


def calc_table_after_para_space(header: Sequence[CellValue], rows: Rows, col_widths: Sequence[int]) -> Spacing:
    lines = _line_counts(header, rows, col_widths) if col_widths else [1]
    return {'spaceBefore': 120 if max(lines) >= 5 else 180, 'spaceAfter': 0}


def calc_row_heights(header: Sequence[CellValue], rows: Rows, col_widths: Sequence[int]) -> list[int]:
    if not col_widths:
        return []
    margins = calc_table_cell_margin(header, rows, col_widths)
    heights = []
    for lines in _line_counts(header, rows, col_widths):
        height = margins['top'] + margins['bottom'] + lines * TABLE_LINE_HEIGHT
        heights.append(max(TABLE_MIN_ROW_HEIGHT, min(TABLE_MAX_ROW_HEIGHT, height)))
    return heights
