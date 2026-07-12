from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from hwpx_layout import TABLE_TOTAL_WIDTH
from table_grid import TableValue
from table_grid import int_rows_value
from table_roles import HEADER_FILL_COLOR
from table_roles import TABLE_ROLE_BASIC
from table_roles import TABLE_ROLE_BUDGET
from table_roles import TABLE_ROLE_COMPARISON
from table_roles import TABLE_ROLE_CRITERIA
from table_roles import TABLE_ROLE_PROGRAM_MATRIX
from table_roles import TABLE_ROLE_SCHEDULE
from table_roles import TABLE_ROLE_TASK_MATRIX
from table_roles import TABLE_ROLE_TWO_COLUMN
from table_roles import infer_table_role
from table_roles import table_widths_for


@dataclass(frozen=True, slots=True)
class TableCellStyle:
    header_align: int = 3
    body_align: int = 1
    header_fill_color: int = HEADER_FILL_COLOR
    border_width: int = 10
    margin_left: int = 510  # 정본 §8-6: 셀 좌우 안여백 1.8mm
    margin_right: int = 510
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
    widths = explicit_widths or table_widths_for(header, rows, role, col_count, total_width)
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
