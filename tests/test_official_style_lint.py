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

    def test_silsigan_is_not_flagged(self):
        # '실시간'은 순화 대상 '실시'가 아니다(오탐 방지)
        blocks = [{"type": "p", "text": "실시간 모니터링을 한다."}]
        notes = converter.lint_official_style(blocks)
        self.assertEqual(notes, [], notes)

    def test_ignores_non_text_blocks(self):
        blocks = [{"type": "table", "header": ["금일"], "rows": []}]
        notes = converter.lint_official_style(blocks)
        self.assertEqual(notes, [])


if __name__ == "__main__":
    unittest.main()
