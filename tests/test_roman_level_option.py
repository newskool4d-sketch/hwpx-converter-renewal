import unittest

import anyway_to_hwpx_com as converter
import hwpx_layout


def _ident(s):
    return s


class RomanLevelParseWiringTests(unittest.TestCase):
    """모듈 글로벌 _ALLOW_ROMAN_LEVEL이 parse_markdown 항목 depth에 반영되는지."""

    def _list_depths(self, text):
        blocks = converter.parse_markdown(text)
        return [b["depth"] for b in blocks if b.get("type") == "li"]

    def test_default_number_depth1(self):
        self.assertEqual(self._list_depths("1. 목적"), [1])

    def test_sihaengmun_number_depth0(self):
        original = converter._ALLOW_ROMAN_LEVEL
        converter._ALLOW_ROMAN_LEVEL = False
        try:
            self.assertEqual(self._list_depths("1. 목적"), [0])
        finally:
            converter._ALLOW_ROMAN_LEVEL = original


class RomanLevelOptionTests(unittest.TestCase):
    # 기본(allow_roman=True): 계획서·보고서 관행 — 로마숫자가 최상위(depth 0)
    def test_default_roman_is_depth0(self):
        r = hwpx_layout.detect_official_list_item("Ⅰ. 총칙", _ident)
        self.assertEqual(r["depth"], 0)

    def test_default_number_is_depth1(self):
        r = hwpx_layout.detect_official_list_item("1. 목적", _ident)
        self.assertEqual(r["depth"], 1)

    # 옵션 OFF(allow_roman=False): 시행문 정본 §2-1 — 1.이 최상위(depth 0)
    def test_no_roman_number_is_depth0(self):
        r = hwpx_layout.detect_official_list_item("1. 목적", _ident, allow_roman=False)
        self.assertEqual(r["depth"], 0)

    def test_no_roman_ga_is_depth1(self):
        r = hwpx_layout.detect_official_list_item("가. 세부", _ident, allow_roman=False)
        self.assertEqual(r["depth"], 1)

    def test_no_roman_circled_is_depth6(self):
        # ㉮ 단계가 8단계 중 마지막(0-index 7 → OFF에서 6)로 한 단계 당겨짐
        r = hwpx_layout.detect_official_list_item("① 항목", _ident, allow_roman=False)
        self.assertEqual(r["depth"], 6)

    def test_no_roman_roman_line_not_matched(self):
        # 시행문 모드에서는 로마숫자 줄을 항목기호로 인식하지 않음
        r = hwpx_layout.detect_official_list_item("Ⅰ. 총칙", _ident, allow_roman=False)
        self.assertIsNone(r)


if __name__ == "__main__":
    unittest.main()
