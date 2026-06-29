import unittest

from table_model import table_layout_for


class RoleTableContentAdaptivityTests(unittest.TestCase):
    """정본 §8-4: 역할(성격) 분류 후 '실제 내용 길이로 2차 보정'.

    역할 매칭 표도 고정 비율이 아니라 내용 길이에 반응해야 한다.
    """

    HEADER = ["항목", "산출내역", "예산액"]

    def test_budget_detail_width_responds_to_content_length(self):
        short_rows = [["강사료", "2시간", "400,000원"]]
        long_rows = [[
            "강사료",
            "초청강사 2명 × 2시간 × 4회차 운영에 따른 표준 단가 적용 산출내역 세부",
            "400,000원",
        ]]

        short = table_layout_for(self.HEADER, short_rows, total_width=10000)
        long = table_layout_for(self.HEADER, long_rows, total_width=10000)

        self.assertEqual(short.table_role, "budget")
        self.assertEqual(long.table_role, "budget")
        # 내용이 길수록 본문 내용(산출내역) 열이 넓어져야 한다
        self.assertGreater(long.column_widths[1], short.column_widths[1])

    def test_budget_short_content_stays_within_profile_baseline(self):
        """짧은 내용일 때 본문 열은 프로파일 기준선(50%)을 초과하지 않는다.

        (잔여 폭은 본문 열이 흡수하되 기준선 위로 부풀지 않음 — 길어질 때만 확장)
        """
        rows = [["강사료", "2시간", "400,000원"]]

        layout = table_layout_for(self.HEADER, rows, total_width=10000)

        self.assertLessEqual(layout.column_widths[1], 5000)

    def test_budget_total_width_preserved(self):
        for rows in ([["강사료", "2시간", "400,000원"]],
                     [["강사료", "초청강사 2명 × 2시간 운영 표준 단가 산출", "400,000원"]]):
            layout = table_layout_for(self.HEADER, rows, total_width=10000)
            self.assertEqual(sum(layout.column_widths), 10000)

    def test_budget_role_keeps_band_around_profile(self):
        """밴드 방식: 내용이 길어도 본문 열이 프로파일 상한(밴드 캡)을 넘지 않는다."""
        long_rows = [[
            "강사료",
            "초청강사 2명 × 2시간 × 4회차 × 3개 학교급 운영에 따른 표준 단가 적용 세부 산출내역 매우 긴 설명",
            "400,000원",
        ]]

        layout = table_layout_for(self.HEADER, long_rows, total_width=10000)

        # budget 3열 프로파일 본문(50%) 기준 밴드 상한(±tolerance) 내
        self.assertLessEqual(layout.column_widths[1], 6500)


if __name__ == "__main__":
    unittest.main()
