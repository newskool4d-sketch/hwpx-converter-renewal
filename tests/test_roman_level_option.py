import ast
import tempfile
import unittest
from pathlib import Path

import anyway_to_hwpx_com as converter
import hwpx_layout


def _ident(s):
    return s


class RomanLevelParseWiringTests(unittest.TestCase):
    """문서유형(doc_type)이 변환 1건 범위에서만 항목 depth에 반영되고 다음 변환으로 새지 않는지."""

    def _list_depths(self, doc_type=None):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "s.md"
            source.write_text("1. 목적\n가. 세부", encoding="utf-8")
            kwargs = {} if doc_type is None else {"doc_type": doc_type}
            blocks = converter.detect_and_parse(source, **kwargs)
        return [b["depth"] for b in blocks if b.get("type") == "li"]

    def test_default_plan_keeps_roman_level(self):
        self.assertEqual(self._list_depths(), [1, 2])

    def test_sihaengmun_starts_at_number_level(self):
        self.assertEqual(self._list_depths("sihaengmun"), [0, 1])

    def test_consecutive_conversions_do_not_leak(self):
        self.assertEqual(self._list_depths("sihaengmun"), [0, 1])
        self.assertEqual(self._list_depths("plan"), [1, 2])
        self.assertTrue(converter._ALLOW_ROMAN_LEVEL.get())

    def test_unknown_doc_type_is_rejected(self):
        with self.assertRaises(ValueError):
            self._list_depths("memo")

    def test_monolith_has_no_global_statement(self):
        tree = ast.parse(Path(converter.__file__).read_text(encoding="utf-8"))
        self.assertEqual([n for n in ast.walk(tree) if isinstance(n, ast.Global)], [])


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
