from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceCell:
    text: str
    row_span: int = 1
    col_span: int = 1


MAX_TABLE_CELLS = 100_000
MAX_COL_SPAN = 1000  # HTML 표준의 colspan 상한


def _span(value: int) -> int:
    return max(1, value)


def _ensure_grid_cell(grid: list[list[str]], row: int, col: int) -> None:
    while len(grid) <= row:
        grid.append([])
    while len(grid[row]) <= col:
        grid[row].append("")


def expand_spanned_rows(rows: list[list[SourceCell]]) -> tuple[list[list[str]], list[list[int]]]:
    grid: list[list[str]] = []
    covered: set[tuple[int, int]] = set()
    merged_cells: list[list[int]] = []
    for row_index, source_row in enumerate(rows):
        _ensure_grid_cell(grid, row_index, 0)
        col_index = 0
        for source_cell in source_row:
            while (row_index, col_index) in covered:
                _ensure_grid_cell(grid, row_index, col_index)
                col_index += 1
            # 병합은 표의 남은 행을 넘을 수 없다 — 과장된 rowspan이 유령 행·메모리 고갈을 만들지 않게 함.
            row_span = min(_span(source_cell.row_span), len(rows) - row_index)
            col_span = min(_span(source_cell.col_span), MAX_COL_SPAN)
            if len(rows) * (col_index + col_span) > MAX_TABLE_CELLS:
                raise ValueError(f'표가 처리 한도({MAX_TABLE_CELLS:,}칸)를 초과했습니다.')
            _ensure_grid_cell(grid, row_index, col_index)
            grid[row_index][col_index] = source_cell.text
            if row_span > 1 or col_span > 1:
                merged_cells.append([row_index, col_index, row_span, col_span])
            for target_row in range(row_index, row_index + row_span):
                for target_col in range(col_index, col_index + col_span):
                    _ensure_grid_cell(grid, target_row, target_col)
                    if target_row == row_index and target_col == col_index:
                        continue
                    grid[target_row][target_col] = ""
                    covered.add((target_row, target_col))
            col_index += col_span
    max_cols = max((len(row) for row in grid), default=0)
    padded = [row + [""] * (max_cols - len(row)) for row in grid]
    return _drop_fully_covered_rows(padded, merged_cells, covered)


def _drop_fully_covered_rows(
    grid: list[list[str]], merged_cells: list[list[int]], covered: set[tuple[int, int]]
) -> tuple[list[list[str]], list[list[int]]]:
    """모든 칸이 병합에 가려진 행은 셀이 하나도 없는 행이 되어 한글이 문서를 열지 못한다.

    그런 행을 빼고 병합 좌표·크기를 남은 행 기준으로 다시 매긴다.
    """
    kept = [
        row_index for row_index, row in enumerate(grid)
        if not row or any((row_index, col_index) not in covered for col_index in range(len(row)))
    ]
    if len(kept) == len(grid):
        return grid, merged_cells
    remapped: list[list[int]] = []
    for row, col, row_span, col_span in merged_cells:
        rows = [index for index, kept_row in enumerate(kept) if row <= kept_row < row + row_span]
        if rows and (len(rows) > 1 or col_span > 1):
            remapped.append([rows[0], col, len(rows), col_span])
    return [grid[row_index] for row_index in kept], remapped


def block_rows_from_grid(grid: list[list[str]]) -> tuple[list[str], list[list[str]]]:
    if not grid:
        return [], []
    return list(grid[0]), [list(row) for row in grid[1:]]


def int_rows_value(value: TableValue | None) -> list[list[int]]:
    if not isinstance(value, list):
        return []
    result: list[list[int]] = []
    for row in value:
        if not isinstance(row, list):
            return []
        values: list[int] = []
        for cell in row:
            if type(cell) is not int:
                return []
            values.append(cell)
        if len(values) == 4 and values[2] > 0 and values[3] > 0:
            result.append(values)
    return result


TableValue = str | int | list[str] | list[int] | list[list[str]] | list[list[int]]
