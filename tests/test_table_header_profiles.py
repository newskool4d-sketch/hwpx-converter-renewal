"""헤더 프로필 9종의 역할·내용 보정 회귀 및 실물 검증용 공통 사례."""

import unittest

from hwpx_layout import TABLE_HEADER_WIDTH_PROFILES
from table_model import table_layout_for


# 가상 일반 명칭만 사용한다. 같은 순서의 표를 samples/table_profiles_9.md에 둔다.
# 실물 검증에서는 각 사례의 short_row와 long_row를 함께 사용할 수 있다.
TABLE_CASES = (
    {
        "id": "category_content",
        "header": ["구분", "내용"],
        "short_row": ["준비", "자료 확인"],
        "long_row": ["현장 운영", "참여 학생의 이동 동선과 활동 장소를 확인하고 담당자별 안내 사항과 비상 연락 체계를 사전에 점검한다."],
        "expected_role": "two_column",
        "base_ratio": [25, 75],
    },
    {
        "id": "category_main_content",
        "header": ["구분", "주요 내용"],
        "short_row": ["안내", "일정 공유"],
        "long_row": ["사전 협의", "학교별 참여 규모와 이동 방법을 확인한 뒤 활동 시간, 집결 장소, 준비물 및 우천 시 운영 방법을 함께 안내한다."],
        "expected_role": "two_column",
        "base_ratio": [25, 75],
    },
    {
        "id": "direction_content",
        "header": ["방향", "내용"],
        "short_row": ["참여", "의견 수렴"],
        "long_row": ["협력 운영", "참여 학교와 운영 기관이 사전 협의를 통해 학생의 요구를 확인하고 활동 과정에서 나온 의견을 다음 운영에 반영한다."],
        "expected_role": "two_column",
        "base_ratio": [25, 75],
    },
    {
        "id": "decision_review",
        "header": ["판단 사항", "검토 내용"],
        "short_row": ["운영 여부", "학교 안내와 현장 운영"],
        "long_row": ["우천 시 실내 대체 활동의 운영 가능 여부", "활동 장소의 수용 규모와 이동 시간을 확인하고 학생의 안전을 확보할 수 있는 대체 활동 및 담당자 배치를 검토한다."],
        "expected_role": "two_column",
        "base_ratio": [30, 70],
    },
    {
        "id": "organization_role",
        "header": ["기관·부서", "역할"],
        "short_row": ["운영팀", "학교 안내와 현장 운영"],
        "long_row": ["체험교육 운영 및 현장 안전관리 협의팀", "학교별 신청 내용을 확인하고 현장 운영 담당자와 학생 이동 동선, 활동 장소, 비상 연락 체계 및 안내 자료를 점검한다."],
        "expected_role": "two_column",
        "base_ratio": [30, 70],
    },
    {
        "id": "question_type",
        "header": ["번호", "문항", "유형"],
        "short_row": ["1", "활동은 유익했습니까?", "선택형"],
        "long_row": ["2", "활동 중 가장 도움이 된 내용과 다음 운영에서 보완할 사항을 구체적인 경험을 바탕으로 작성해 주십시오.", "서술형"],
        "expected_role": "basic",
        "base_ratio": [10, 75, 15],
    },
    {
        "id": "time_content_owner",
        "header": ["시간", "내용", "담당"],
        "short_row": ["09:00", "등록 및 안내", "운영팀"],
        "long_row": ["09:30", "학생별 준비 상태와 참여 인원을 확인하고 활동 장소별 이동 방법 및 비상 상황에서의 연락 절차를 안내한다.", "진행팀"],
        "expected_role": "basic",
        "base_ratio": [20, 60, 20],
    },
    {
        "id": "stage_content_period",
        "header": ["단계", "내용", "시기"],
        "short_row": ["준비", "수요 확인", "운영 전"],
        "long_row": ["운영 점검", "학교별 참여 현황과 활동 장소의 준비 상태를 확인하고 추가 안내가 필요한 사항을 정리하여 담당자에게 전달한다.", "운영 중"],
        "expected_role": "task_matrix",
        "base_ratio": [18, 62, 20],
    },
    {
        "id": "category_people_role",
        "header": ["구분", "인원", "역할"],
        "short_row": ["운영팀", "3명", "접수 안내"],
        "long_row": ["안전관리팀", "5명", "참여 학생의 집결과 이동을 안내하고 활동 장소별 안전 상태를 확인하며 비상 상황 발생 시 담당자에게 즉시 연락한다."],
        "expected_role": "basic",
        "base_ratio": [20, 15, 65],
    },
)

LONG_TEXT = "체험활동 참여 학생의 이동 동선과 집결 장소 및 비상 연락 체계 사전 확인"
THIRTY_SEVENTY_CASES = tuple(case for case in TABLE_CASES if case["base_ratio"] == [30, 70])


class HeaderProfileRegressionTests(unittest.TestCase):
    def assert_valid_widths(self, layout, count, total):
        self.assertEqual(len(layout.column_widths), count)
        self.assertTrue(all(width > 0 for width in layout.column_widths))
        self.assertEqual(sum(layout.column_widths), total)

    def test_cases_cover_all_nine_header_profiles(self):
        self.assertEqual(len(TABLE_CASES), 9)
        self.assertEqual(
            {tuple(case["header"]) for case in TABLE_CASES},
            set(TABLE_HEADER_WIDTH_PROFILES),
        )

    def test_nine_profiles_keep_roles_and_usable_widths_for_short_and_long_rows(self):
        for case in TABLE_CASES:
            for total in (10000, 14000):
                for name, rows in (
                    ("short", [case["short_row"]]),
                    ("long", [case["long_row"]]),
                    ("mixed", [case["short_row"], case["long_row"]]),
                ):
                    with self.subTest(case=case["id"], rows=name, total=total):
                        layout = table_layout_for(case["header"], rows, total_width=total)
                        self.assertEqual(layout.table_role, case["expected_role"])
                        self.assert_valid_widths(layout, len(case["header"]), total)

    def test_people_and_organization_words_are_not_currency_units(self):
        for label in ("인원", "참여 인원", "인원(명)", "정원", "위원", "위원회", "교원", "구성원", "원장", "지원", "지원청"):
            with self.subTest(label=label):
                layout = table_layout_for(["구분", label, "역할"], [["운영팀", "3", "안내"]])
                self.assertEqual(layout.table_role, "basic")

    def test_standalone_currency_units_still_identify_budget_tables(self):
        for label in ("원", "천원", "만원", "백만원", "천만원", "억원", "단위: 원", "규모(천원)", "규모(백만원)", "규모 [억원]"):
            with self.subTest(label=label):
                layout = table_layout_for(["항목", "내역", label], [["강사료", "2시간", "400"]])
                self.assertEqual(layout.table_role, "budget")

    def test_existing_budget_headers_keep_their_role(self):
        for label in ("예산", "예산액", "금액", "단가", "수량", "합계", "amount", "price", "total"):
            with self.subTest(label=label):
                layout = table_layout_for(["항목", "내역", label], [["강사료", "2시간", "400"]])
                self.assertEqual(layout.table_role, "budget")

    def test_thirty_seventy_tables_keep_their_band_and_respond_to_either_column(self):
        for case in THIRTY_SEVENTY_CASES:
            with self.subTest(case=case["id"]):
                short_row = case["short_row"]
                rows_to_check = (
                    [short_row],
                    [[LONG_TEXT, short_row[1]]],
                    [[short_row[0], LONG_TEXT]],
                    [case["short_row"], case["long_row"]],
                )
                layouts = [table_layout_for(case["header"], rows, total_width=10000) for rows in rows_to_check]
                for layout in layouts:
                    self.assertEqual(layout.table_role, "two_column")
                    # 30% 기준선에 기존 내용 보정 허용 범위(-15%, +30%)를 유지한다.
                    self.assertGreaterEqual(layout.column_widths[0], 2550)
                    self.assertLessEqual(layout.column_widths[0], 3900)
                    self.assert_valid_widths(layout, 2, 10000)
                short, long_first, long_second, _ = layouts
                self.assertGreater(long_first.column_widths[0], short.column_widths[0])
                self.assertGreater(long_second.column_widths[1], short.column_widths[1])

    def test_explicit_widths_override_content_adjustment(self):
        for case in THIRTY_SEVENTY_CASES:
            with self.subTest(case=case["id"]):
                layout = table_layout_for(
                    case["header"], [case["long_row"]], column_widths=[4, 6], total_width=10000,
                )
                self.assertEqual(layout.column_widths, [4000, 6000])


if __name__ == "__main__":
    unittest.main()
