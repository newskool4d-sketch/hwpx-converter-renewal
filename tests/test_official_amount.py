import unittest

import anyway_to_hwpx_com as converter


class SinoKoreanAmountTests(unittest.TestCase):
    def test_spec_example_113560(self):
        # 정본 §1-2 예시
        self.assertEqual(converter._sino_korean_amount(113560), "일십일만삼천오백육십")

    def test_small_numbers(self):
        self.assertEqual(converter._sino_korean_amount(0), "영")
        self.assertEqual(converter._sino_korean_amount(7), "칠")
        self.assertEqual(converter._sino_korean_amount(10), "일십")
        self.assertEqual(converter._sino_korean_amount(100), "일백")

    def test_man_boundary(self):
        self.assertEqual(converter._sino_korean_amount(10000), "일만")
        self.assertEqual(converter._sino_korean_amount(400000), "사십만")

    def test_eok(self):
        self.assertEqual(converter._sino_korean_amount(100000000), "일억")


class NormalizeOfficialAmountsTests(unittest.TestCase):
    def test_adds_hangul_paren_to_amount(self):
        blocks = [{"type": "p", "text": "강사료 113,560원 지급"}]
        result = converter.normalize_official_amounts(blocks)
        self.assertEqual(result[0]["text"], "강사료 금113,560원(금일십일만삼천오백육십원) 지급")

    def test_already_annotated_is_left_untouched(self):
        text = "금113,560원(금일십일만삼천오백육십원)"
        blocks = [{"type": "p", "text": text}]
        result = converter.normalize_official_amounts(blocks)
        self.assertEqual(result[0]["text"], text)

    def test_non_amount_numbers_untouched(self):
        blocks = [{"type": "p", "text": "참가 인원 113,560명"}]
        result = converter.normalize_official_amounts(blocks)
        self.assertEqual(result[0]["text"], "참가 인원 113,560명")


if __name__ == "__main__":
    unittest.main()
