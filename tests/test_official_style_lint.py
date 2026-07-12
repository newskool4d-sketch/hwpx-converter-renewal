import unittest

import anyway_to_hwpx_com as converter


def _has(notes, *needles):
    """notes 리스트 중 모든 needle을 포함하는 항목이 하나라도 있으면 True."""
    return any(all(n in note for n in needles) for note in notes)


class LintOfficialStyleTests(unittest.TestCase):
    def test_flags_geumil_suggests_oneul(self):
        # 정본 §1-1 순화: 금일 → 오늘
        blocks = [{"type": "p", "text": "금일 회의를 개최함."}]
        notes = converter.lint_official_style(blocks)
        self.assertTrue(_has(notes, "금일", "오늘"), notes)

    def test_flags_silsi_phrase(self):
        # 정본 §1-1 순화: ○을 실시한다 → ○을 한다
        blocks = [{"type": "p", "text": "안전 점검을 실시한다."}]
        notes = converter.lint_official_style(blocks)
        self.assertTrue(any("실시" in note for note in notes), notes)

    def test_flags_mit_parallel(self):
        # 정본 §1-1: '및'의 병렬관계 → 와/과/·
        blocks = [{"type": "p", "text": "계획 수립 및 예산 편성"}]
        notes = converter.lint_official_style(blocks)
        self.assertTrue(_has(notes, "및"), notes)

    def test_clean_text_returns_empty(self):
        blocks = [{"type": "p", "text": "오늘 회의를 앞으로 진행한다."}]
        notes = converter.lint_official_style(blocks)
        self.assertEqual(notes, [])

    def test_distinct_expression_reported_once(self):
        blocks = [
            {"type": "p", "text": "금일 회의"},
            {"type": "p", "text": "금일 오후 보고"},
        ]
        notes = converter.lint_official_style(blocks)
        geumil_notes = [n for n in notes if "금일" in n]
        self.assertEqual(len(geumil_notes), 1, notes)

    def test_sino_amount_reading_not_flagged_as_geumil(self):
        # 금액 한글병기 '금일백육십만원' 속 '금일'은 순화 대상 '금일(오늘)'이 아니다
        blocks = [{"type": "p", "text": "강사료 금1,600,000원(금일백육십만원) 지급"}]
        notes = converter.lint_official_style(blocks)
        self.assertFalse(any("금일" in n for n in notes), notes)

    def test_real_geumil_still_flagged(self):
        # 진짜 '금일 회의'는 여전히 경고
        blocks = [{"type": "p", "text": "금일 회의를 개최함."}]
        notes = converter.lint_official_style(blocks)
        self.assertTrue(_has(notes, "금일", "오늘"), notes)

    def test_silsigan_is_not_flagged(self):
        # '실시간'은 순화 대상 '실시'가 아니다(오탐 방지)
        blocks = [{"type": "p", "text": "실시간 모니터링을 한다."}]
        notes = converter.lint_official_style(blocks)
        self.assertEqual(notes, [], notes)

    def test_ignores_non_text_blocks(self):
        blocks = [{"type": "table", "header": ["금일"], "rows": []}]
        notes = converter.lint_official_style(blocks)
        self.assertEqual(notes, [])


class LintMoneyNotationTests(unittest.TestCase):
    """정본 §1-2 금액 표기 — '천원' 축약 경고 (kordoc 표기법 린트 대응).

    금액은 '천원'으로 줄이지 않고 아라비아 숫자로 적는다(예: 345,000원).
    예산액은 대부분 표 안에 나오므로 표 셀까지 스캔한다.
    """

    def test_flags_cheonwon_in_text_block(self):
        blocks = [{"type": "p", "text": "강사료 400천원 지급"}]
        notes = converter.lint_money_notation(blocks)
        self.assertTrue(_has(notes, "천원"), notes)

    def test_flags_cheonwon_with_comma_in_table_cell(self):
        blocks = [{"type": "table", "header": ["항목", "예산"], "rows": [["강사료", "3,400천원"]]}]
        notes = converter.lint_money_notation(blocks)
        self.assertTrue(_has(notes, "천원"), notes)

    def test_clean_amount_not_flagged(self):
        blocks = [{"type": "p", "text": "강사료 345,000원 지급"}]
        notes = converter.lint_money_notation(blocks)
        self.assertEqual(notes, [])

    def test_cheonwon_without_leading_digit_not_flagged(self):
        # '수천원'·'천원짜리'처럼 숫자가 앞에 없는 경우는 축약 표기가 아님
        blocks = [{"type": "p", "text": "수천원 규모의 소액 지출"}]
        notes = converter.lint_money_notation(blocks)
        self.assertEqual(notes, [])

    def test_reported_once_across_blocks(self):
        blocks = [
            {"type": "table", "header": ["항목", "예산"], "rows": [["강사료", "400천원"], ["재료비", "800천원"]]},
        ]
        notes = converter.lint_money_notation(blocks)
        cheonwon_notes = [n for n in notes if "천원" in n]
        self.assertEqual(len(cheonwon_notes), 1, notes)


if __name__ == "__main__":
    unittest.main()
