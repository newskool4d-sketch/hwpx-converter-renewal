from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from hwpx_layout import calc_col_widths
from hwpx_layout import visual_width


TABLE_ROLE_BASIC: Final = "basic"
TABLE_ROLE_SCHEDULE: Final = "schedule"
TABLE_ROLE_BUDGET: Final = "budget"
TABLE_ROLE_PROGRAM_MATRIX: Final = "program_matrix"
TABLE_ROLE_TASK_MATRIX: Final = "task_matrix"
TABLE_ROLE_COMPARISON: Final = "comparison"
TABLE_ROLE_CRITERIA: Final = "criteria"
TABLE_ROLE_TWO_COLUMN: Final = "two_column"

HEADER_FILL_COLOR: Final = 0xC8C8C8  # 정본 §8-2: 헤더 회색 배경 RGB 200
SCHEDULE_HEADER: Final = ("시작", "종료", "분", "내용", "담당")

BUDGET_HEADER_TERMS: Final = ("예산", "예산액", "금액", "단가", "수량", "합계", "원", "amount", "price", "total")
TIME_HEADER_TERMS: Final = ("시작", "종료", "시간", "시각", "일시", "분", "소요")
PROGRAM_HEADER_TERMS: Final = ("프로그램", "학교급", "대상", "운영 형태", "중심", "편성", "고도화")
TASK_HEADER_TERMS: Final = ("추진 과제", "핵심 내용", "주요 내용", "추진 내용", "주요 방법", "기대 효과", "단계", "과제")
COMPARISON_HEADER_TERMS: Final = ("기존", "현재", "한계", "개선", "방향", "비교")
CRITERIA_HEADER_TERMS: Final = ("지표", "측정", "평가", "심사", "배점")
TWO_COLUMN_DETAIL_TERMS: Final = ("내용", "사항", "확인", "방향", "역할", "시기", "일정", "계획")
DETAIL_HEADER_TERMS: Final = ("내용", "세부", "내역", "설명", "비고", "추진", "계획", "방향", "효과")

ROLE_WIDTH_PROFILES: Final[dict[str, dict[int, tuple[int, ...]]]] = {
    TABLE_ROLE_SCHEDULE: {5: (14, 14, 9, 49, 14)},
    TABLE_ROLE_BUDGET: {3: (24, 50, 26), 4: (22, 42, 20, 16)},
    TABLE_ROLE_PROGRAM_MATRIX: {3: (22, 26, 52), 4: (16, 22, 28, 34), 5: (14, 19, 23, 22, 22)},
    TABLE_ROLE_TASK_MATRIX: {3: (16, 30, 54), 4: (15, 25, 25, 35), 5: (14, 21, 21, 22, 22), 6: (14, 17, 17, 17, 17, 18)},
    TABLE_ROLE_COMPARISON: {3: (16, 42, 42), 4: (14, 23, 23, 40)},
    TABLE_ROLE_CRITERIA: {3: (20, 50, 30), 4: (16, 34, 30, 20)},
    TABLE_ROLE_TWO_COLUMN: {2: (25, 75)},
}


def _joined_header(header: Sequence[str]) -> str:
    return " ".join(cell.strip() for cell in header).lower()


def _has_any(text: str, terms: Sequence[str]) -> bool:
    return any(term.lower() in text for term in terms)


def _term_count(text: str, terms: Sequence[str]) -> int:
    return sum(1 for term in terms if term.lower() in text)


def _row_starts_with_time(row: Sequence[str]) -> bool:
    if not row:
        return False
    first = row[0].strip()
    return ":" in first and any(char.isdigit() for char in first)


def _is_schedule(header: Sequence[str], rows: Sequence[Sequence[str]]) -> bool:
    normalized_header = tuple(cell.strip() for cell in header)
    joined = _joined_header(header)
    if normalized_header == SCHEDULE_HEADER:
        return True
    if _term_count(joined, TIME_HEADER_TERMS) >= 2:
        return True
    return len(normalized_header) == 5 and bool(rows) and all(_row_starts_with_time(row) for row in rows)


def infer_table_role(header: list[str], rows: list[list[str]]) -> str:
    col_count = max((len(row) for row in ([header] if header else []) + rows), default=0)
    joined = _joined_header(header)
    if not joined:
        return TABLE_ROLE_BASIC
    if _is_schedule(header, rows):
        return TABLE_ROLE_SCHEDULE
    if _has_any(joined, BUDGET_HEADER_TERMS):
        return TABLE_ROLE_BUDGET
    if col_count == 2 and _has_any(joined, TWO_COLUMN_DETAIL_TERMS):
        return TABLE_ROLE_TWO_COLUMN
    if _has_any(joined, CRITERIA_HEADER_TERMS):
        return TABLE_ROLE_CRITERIA
    if _term_count(joined, COMPARISON_HEADER_TERMS) >= 2:
        return TABLE_ROLE_COMPARISON
    if _has_any(joined, PROGRAM_HEADER_TERMS) and _has_any(joined, ("프로그램", "고도화", "편성", "운영")):
        return TABLE_ROLE_PROGRAM_MATRIX
    if _has_any(joined, TASK_HEADER_TERMS):
        return TABLE_ROLE_TASK_MATRIX
    return TABLE_ROLE_BASIC


def _scale_profile(profile: Sequence[int], total_width: int) -> list[int]:
    profile_sum = sum(profile)
    if profile_sum <= 0:
        return []
    widths = [max(1, int(total_width * value / profile_sum)) for value in profile]
    widths[max(range(len(widths)), key=lambda index: profile[index])] += total_width - sum(widths)
    return widths


def _role_profile(table_role: str, col_count: int) -> list[int]:
    return list(ROLE_WIDTH_PROFILES.get(table_role, {}).get(col_count, ()))


def _long_text_target_col(header: Sequence[str], rows: Sequence[Sequence[str]], col_count: int) -> int:
    scores: list[int] = []
    for col_index in range(col_count):
        header_text = header[col_index] if col_index < len(header) else ""
        values = [row[col_index] for row in rows if col_index < len(row)]
        score = max([visual_width(header_text), *[visual_width(value) for value in values]], default=0)
        if any(term in header_text for term in DETAIL_HEADER_TERMS):
            score += 16
        scores.append(score)
    if not scores or max(scores) < 48:
        return -1
    return max(range(len(scores)), key=lambda index: scores[index])


def _expand_long_text_width(widths: list[int], header: Sequence[str], rows: Sequence[Sequence[str]], total_width: int) -> list[int]:
    target_col = _long_text_target_col(header, rows, len(widths))
    if target_col < 0:
        return widths
    result = list(widths)
    target_width = max(result[target_col], int(total_width * 0.50))
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


def _is_detail_column(header_text: str, col_count: int, col_index: int) -> bool:
    if any(term in header_text for term in DETAIL_HEADER_TERMS):
        return True
    return col_count >= 3 and col_index == col_count - 1


def _redistribute_to_bounds(widths: list[int], min_bounds: list[int], max_bounds: list[int], total_width: int) -> list[int]:
    result = [max(min_bounds[index], min(max_bounds[index], width)) for index, width in enumerate(widths)]
    while sum(result) > total_width:
        candidates = [index for index, width in enumerate(result) if width > min_bounds[index]]
        if not candidates:
            break
        index = max(candidates, key=lambda item: result[item] - min_bounds[item])
        result[index] -= 1
    while sum(result) < total_width:
        candidates = [index for index, width in enumerate(result) if width < max_bounds[index]]
        if not candidates:
            break
        index = max(candidates, key=lambda item: max_bounds[item] - result[item])
        result[index] += 1
    if result and sum(result) != total_width:
        result[max(range(len(result)), key=lambda index: result[index])] += total_width - sum(result)
    return result


def _clamp_widths(widths: list[int], header: Sequence[str], total_width: int) -> list[int]:
    col_count = len(widths)
    if col_count <= 1:
        return widths
    min_bounds = [max(700, int(total_width * 0.07)) for _ in range(col_count)]
    max_bounds = [total_width for _ in range(col_count)]
    if col_count == 2:
        min_bounds[0] = max(min_bounds[0], int(total_width * 0.22))
        max_bounds[1] = min(max_bounds[1], int(total_width * 0.78))
    elif col_count >= 3:
        min_bounds[0] = max(min_bounds[0], int(total_width * 0.12))
    for col_index in range(col_count):
        header_text = header[col_index] if col_index < len(header) else ""
        if _is_detail_column(header_text, col_count, col_index):
            ratio = 0.56 if col_count == 3 else 0.46
            max_bounds[col_index] = min(max_bounds[col_index], int(total_width * ratio))
    return _redistribute_to_bounds(widths, min_bounds, max_bounds, total_width)


ROLE_BAND_SHRINK: Final = 0.15
ROLE_BAND_GROW: Final = 0.30


def _blend_profile_with_content(profile_w: list[int], content: list[int], total_width: int) -> list[int]:
    """정본 §8-4: 역할 프로파일을 비대칭 밴드(경계)로, 실제 내용 폭을 목표로 보정.

    프로파일은 열의 '성격(역할)' 기준선이다. 내용 길이에 반응시키되 비대칭으로:
    - 축소는 보수적(−15%) — 구분·식별 등 구조 열이 정본 §8-4 하한을 깨지 않게.
    - 확장은 관대(+30%) — 본문 내용 열이 내용 분량에 따라 넓어지게.
    """
    if not content or len(content) != len(profile_w):
        return profile_w
    min_bounds = [max(1, int(width * (1.0 - ROLE_BAND_SHRINK))) for width in profile_w]
    max_bounds = [int(width * (1.0 + ROLE_BAND_GROW)) for width in profile_w]
    return _redistribute_to_bounds(content, min_bounds, max_bounds, total_width)


def table_widths_for(
    header: list[str],
    rows: list[list[str]],
    table_role: str,
    col_count: int,
    total_width: int,
) -> list[int]:
    if col_count <= 0:
        return []
    calculated = calc_col_widths(header, rows, total=total_width)
    profile = _role_profile(table_role, col_count)
    if profile:
        profile_w = _scale_profile(profile, total_width)
        return _blend_profile_with_content(profile_w, calculated, total_width)
    return _clamp_widths(_expand_long_text_width(calculated, header, rows, total_width), header, total_width)
