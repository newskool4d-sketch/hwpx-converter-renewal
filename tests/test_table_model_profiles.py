import unittest

from table_model import table_layout_for


class PublicDocumentTableProfileTests(unittest.TestCase):
    def test_program_matrix_keeps_description_column_from_swallowing_middle_columns(self):
        header = ["구분", "운영 형태", "중심 프로그램", "편성 기조"]
        rows = [
            ["초등", "방문체험 중심", "역사문화체험, 생태탐방교육", "학교 수요가 높은 체험교육을 우선 편성"],
            ["중·고등", "숙박체험 중심", "도전활동, 진로캠프", "창의성과 공동체성을 기르는 방향으로 운영"],
        ]

        layout = table_layout_for(header, rows, total_width=10000)

        self.assertEqual(layout.table_role, "program_matrix")
        self.assertEqual(sum(layout.column_widths), 10000)
        self.assertGreaterEqual(layout.column_widths[0], 1200)
        self.assertLessEqual(layout.column_widths[-1], 4200)
        self.assertGreaterEqual(sum(layout.column_widths[1:3]), 4300)

    def test_task_matrix_balances_task_and_content_columns(self):
        header = ["구분", "추진 과제", "핵심 내용"]
        rows = [
            ["과제 1", "방문형 체험학습 확대 운영", "초등 방문체험 및 중·고등 숙박형 체험 확대"],
            ["과제 2", "학교급별 체험교육 프로그램 고도화", "학교급별 운영 특성을 반영한 프로그램 재구조화"],
        ]

        layout = table_layout_for(header, rows, total_width=10000)

        self.assertEqual(layout.table_role, "task_matrix")
        self.assertEqual(sum(layout.column_widths), 10000)
        self.assertGreaterEqual(layout.column_widths[0], 1200)
        self.assertGreaterEqual(layout.column_widths[1], 2200)
        # 본문 내용 열 상한 = 정본 §8-4 본문 65%(6500). 밴드 재기준화(구 5600).
        self.assertLessEqual(layout.column_widths[2], 6500)

    def test_comparison_table_preserves_before_after_columns(self):
        header = ["구분", "기존 운영", "개선 방향", "주요 내용"]
        rows = [
            ["운영", "기관 중심 운영", "학교 수요 기반 운영", "학교급별 수요와 현장 여건을 반영"],
            ["프로그램", "개별 프로그램 운영", "연계형 프로그램 운영", "방문형과 숙박형 체험을 연계"],
        ]

        layout = table_layout_for(header, rows, total_width=10000)

        self.assertEqual(layout.table_role, "comparison")
        self.assertEqual(sum(layout.column_widths), 10000)
        # 짧은 라벨(운영/프로그램) 구분 열의 가독 하한. 밴드 재기준화(구 1200).
        self.assertGreaterEqual(layout.column_widths[0], 1000)
        self.assertGreaterEqual(layout.column_widths[1], 1900)
        self.assertGreaterEqual(layout.column_widths[2], 1900)
        self.assertLessEqual(layout.column_widths[3], 4600)

    def test_two_column_checklist_keeps_label_column_readable(self):
        header = ["구분", "확인 필요 사항"]
        rows = [
            ["예산", "세부 산출내역과 재원 배분 기준 확인"],
            ["운영", "학교급별 신청 수요와 운영 가능 인원 확인"],
        ]

        layout = table_layout_for(header, rows, total_width=10000)

        self.assertEqual(layout.table_role, "two_column")
        self.assertEqual(sum(layout.column_widths), 10000)
        self.assertGreaterEqual(layout.column_widths[0], 2200)
        self.assertLessEqual(layout.column_widths[1], 7800)

    def test_three_column_direction_table_keeps_main_content_readable(self):
        header = ["구분", "주요 내용", "운영 방향"]
        rows = [
            ["운영", "학교 수요를 반영한 체험교육 운영", "학교급별 특성에 맞게 운영"],
            ["지원", "안전관리와 사전 안내 강화", "현장 부담을 줄이는 방향으로 개선"],
        ]

        layout = table_layout_for(header, rows, total_width=10000)

        self.assertEqual(layout.table_role, "task_matrix")
        self.assertEqual(sum(layout.column_widths), 10000)
        self.assertGreaterEqual(layout.column_widths[0], 1200)
        self.assertGreaterEqual(layout.column_widths[1], 2600)
        self.assertLessEqual(layout.column_widths[2], 5600)


if __name__ == "__main__":
    unittest.main()
