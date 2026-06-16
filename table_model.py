from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from hwpx_layout import TABLE_TOTAL_WIDTH
from hwpx_layout import calc_col_widths
from hwpx_layout import visual_width
from table_grid import TableValue
from table_grid import int_rows_value


TABLE_ROLE_BASIC: Final = "basic"
TABLE_ROLE_SCHEDULE: Final = "schedule"
TABLE_ROLE_BUDGET: Final = "budget"
SCHEDULE_COLUMN_WIDTHS: Final = (14, 14, 9, 49, 14)
BUDGET_COLUMN_WIDTHS_BY_COUNT: Final = {3: (24, 50, 26), 4: (22, 42, 20, 16)}
HEADER_FILL_COLOR: Final = 0xE7E7E7
SCHEDULE_HEADER: Final = ("시작", "종료", "분", "내용", "담당")
BUDGET_HEADER_TERMS: Final = ("예산", "예산액", "금액", "단가", "수량", "합계", "원", "amount", "price", "total")
SCHEDULE_HEADER_TERMS: Final = ("시작", "종료", "시간", "시각", "일시", "분", "내용", "담당")
DETAIL_HEADER_TERMS: Final = ("내용", "세부", "내역", "설명", "비고", "추진", "계획")


@dataclass(frozen=True, slots=True)
class TableCellStyle:
    header_align: int = 3
    body_align: int = 1
    header_fill_color: int = HEADER_FILL_COLOR
    border_width: int = 10
    margin_left: int = 170
    margin_right: int = 170
    margin_top: int = 120
    margin_bottom: int = 120


@dataclass(frozen=True, slots=True)
class TableLayout:
    header: list[str]
    rows: list[list[str]]
    table_role: str
    column_widths: list[int]
    style: TableCellStyle
    table_source: str
    worksheet_title: str
    merged_cells: list[list[int]]


TableBlock = Mapping[str, TableValue]


def _string_list_value(value: TableValue | None) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            return []
        result.append(item)
    return result


def _string_rows_value(value: TableValue | None) -> list[list[str]]:
    if not isinstance(value, list):
        return []
    result: list[list[str]] = []
    for row in value:
        if not isinstance(row, list):
            return []
        values: list[str] = []
        for cell in row:
            if not isinstance(cell, str):
                return []
            values.append(cell)
        result.append(values)
    return result


def _int_list_value(value: TableValue | None) -> list[int]:
    if not isinstance(value, list):
        return []
    result: list[int] = []
    for item in value:
        if type(item) is not int:
            return []
        result.append(item)
    return result


def _col_count(header: list[str], rows: list[list[str]]) -> int:
    return max((len(row) for row in ([header] if header else []) + rows), default=0)


def _scale_widths(widths: list[int], col_count: int, total_width: int) -> list[int]:
    if col_count <= 0 or len(widths) != col_count or any(width <= 0 for width in widths):
        return []
    width_sum = sum(widths)
    if width_sum <= 0:
        return []
    scaled = [max(1, int(total_width * width / width_sum)) for width in widths]
    diff = total_width - sum(scaled)
    if diff:
        scaled[max(range(len(widths)), key=lambda index: widths[index])] += diff
    return scaled


def infer_table_role(header: list[str], rows: list[list[str]]) -> str:
    normalized_header = tuple(cell.strip() for cell in header)
    if normalized_header == SCHEDULE_HEADER:
        return TABLE_ROLE_SCHEDULE
    joined_header = " ".join(normalized_header).lower()
    if any(term in joined_header for term in BUDGET_HEADER_TERMS):
        return TABLE_ROLE_BUDGET
    if len(normalized_header) >= 3 and any(term in joined_header for term in SCHEDULE_HEADER_TERMS):
        return TABLE_ROLE_SCHEDULE
    if len(normalized_header) == 5 and rows and all(":" in row[0] for row in rows if row):
        return TABLE_ROLE_SCHEDULE
    return TABLE_ROLE_BASIC


def _role_profile(table_role: str, col_count: int) -> list[int]:
    if table_role == TABLE_ROLE_SCHEDULE and col_count == len(SCHEDULE_COLUMN_WIDTHS):
        return list(SCHEDULE_COLUMN_WIDTHS)
    if table_role == TABLE_ROLE_BUDGET:
        return list(BUDGET_COLUMN_WIDTHS_BY_COUNT.get(col_count, ()))
    return []


def _fit_width_count(widths: list[int], col_count: int, total_width: int) -> list[int]:
    if col_count <= 0:
        return []
    if len(widths) != col_count:
        result = [max(1, total_width // col_count) for _ in range(col_count)]
        result[-1] += total_width - sum(result)
        return result
    result = list(widths)
    diff = total_width - sum(result)
    if diff:
        result[max(range(len(result)), key=lambda index: result[index])] += diff
    return result


def _long_text_target_col(header: list[str], rows: list[list[str]], col_count: int) -> int:
    scores: list[int] = []
    for col_index in range(col_count):
        header_text = header[col_index] if col_index < len(header) else ""
        values = [row[col_index] for row in rows if col_index < len(row)]
        score = max([visual_width(header_text), *[visual_width(value) for value in values]], default=0)
        if any(term in header_text for term in DETAIL_HEADER_TERMS):
            score += 18
        scores.append(score)
    if not scores or max(scores) < 48:
        return -1
    return max(range(len(scores)), key=lambda index: scores[index])


def _expand_long_text_width(widths: list[int], header: list[str], rows: list[list[str]], total_width: int) -> list[int]:
    target_col = _long_text_target_col(header, rows, len(widths))
    if target_col < 0:
        return widths
    result = list(widths)
    target_width = max(result[target_col], int(total_width * 0.55))
    overflow = target_width - result[target_col]
    if overflow <= 0:
        return result
    result[target_col] = target_width
    min_width = max(800, int(total_width * 0.08))
    shrinkable = [index for index in range(len(result)) if index != target_col and result[index] > min_width]
    while overflow > 0 and shrinkable:
        changed = False
        for index in shrinkable:
            if overflow <= 0:
                break
            if result[index] > min_width:
                result[index] -= 1
                overflow -= 1
                changed = True
        if not changed:
            break
    result[target_col] += total_width - sum(result)
    return result


def table_layout_for(
    header: list[str],
    rows: list[list[str]],
    table_role: str | None = None,
    column_widths: list[int] | None = None,
    table_source: str | None = None,
    worksheet_title: str | None = None,
    merged_cells: list[list[int]] | None = None,
    total_width: int = TABLE_TOTAL_WIDTH,
) -> TableLayout:
    col_count = _col_count(header, rows)
    role = table_role.strip() if table_role and table_role.strip() else infer_table_role(header, rows)
    explicit_widths = _scale_widths(column_widths or [], col_count, total_width)
    role_widths = _scale_widths(_role_profile(role, col_count), col_count, total_width)
    calculated_widths = calc_col_widths(header, rows, total=total_width)
    widths = explicit_widths or role_widths or _expand_long_text_width(calculated_widths, header, rows, total_width)
    return TableLayout(
        header=list(header),
        rows=[list(row) for row in rows],
        table_role=role,
        column_widths=_fit_width_count(widths, col_count, total_width),
        style=TableCellStyle(),
        table_source=table_source or "",
        worksheet_title=worksheet_title or "",
        merged_cells=[list(span) for span in (merged_cells or [])],
    )


def table_layout_from_block(block: TableBlock, total_width: int = TABLE_TOTAL_WIDTH) -> TableLayout:
    role_value = block.get("table_role")
    source_value = block.get("table_source")
    title_value = block.get("worksheet_title")
    return table_layout_for(
        _string_list_value(block.get("header")),
        _string_rows_value(block.get("rows")),
        role_value if isinstance(role_value, str) else None,
        _int_list_value(block.get("column_widths")),
        source_value if isinstance(source_value, str) else None,
        title_value if isinstance(title_value, str) else None,
        int_rows_value(block.get("merged_cells")) or int_rows_value(block.get("merges")),
        total_width=total_width,
    )
