import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import anyway_to_hwpx_com as converter


class ParserTests(unittest.TestCase):
    def test_markdown_detects_heading_table_and_list(self):
        blocks = converter.parse_markdown(
            "# 제목\n\n"
            "| 이름 | 값 |\n"
            "|---|---|\n"
            "| 테스트 | 1 |\n\n"
            "- 항목\n"
        )

        self.assertEqual(blocks[0], {"type": "h", "level": 1, "text": "제목"})
        self.assertEqual(blocks[1]["type"], "table")
        self.assertEqual(blocks[1]["header"], ["이름", "값"])
        self.assertEqual(blocks[2]["type"], "li")

    def test_plain_text_detects_korean_numbered_list(self):
        blocks = converter.parse_plain_text("가. 첫째\n나. 둘째")

        self.assertEqual([block["type"] for block in blocks], ["li", "li"])
        self.assertEqual(blocks[0]["depth"], 1)


class OutputPathTests(unittest.TestCase):
    def test_build_output_path_avoids_existing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "sample.md"
            src.write_text("# sample", encoding="utf-8")
            (root / "sample.hwpx").write_text("", encoding="utf-8")
            (root / "sample - 2.hwpx").write_text("", encoding="utf-8")

            out = converter.build_output_path(src, root)

        self.assertEqual(out.name, "sample - 3.hwpx")


class TableLayoutTests(unittest.TestCase):
    def test_column_widths_are_positive_and_sum_to_total(self):
        header = ["번호", "소속", "성명", "추진내용", "비고"]
        rows = [["1", "인천교육청", "홍길동", "세부 추진 내용을 길게 적습니다.", "확인"]]

        widths = converter.calc_col_widths(header, rows)

        self.assertEqual(sum(widths), converter.TABLE_TOTAL_WIDTH)
        self.assertTrue(all(width > 0 for width in widths))

    def test_row_heights_match_table_rows(self):
        header = ["번호", "추진내용"]
        rows = [["1", "긴 내용 " * 20]]
        widths = converter.calc_col_widths(header, rows)

        heights = converter.calc_row_heights(header, rows, widths)

        self.assertEqual(len(heights), 2)
        self.assertTrue(all(height >= converter.TABLE_MIN_ROW_HEIGHT for height in heights))


class OcrPathTests(unittest.TestCase):
    def test_resolve_kordoc_dir_uses_explicit_path_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            resolved = converter.resolve_kordoc_dir(tmp)

        self.assertEqual(resolved, Path(tmp).resolve())

    def test_resolve_kordoc_dir_uses_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"KORDOC_HOME": tmp}, clear=False):
                resolved = converter.resolve_kordoc_dir()

        self.assertEqual(resolved, Path(tmp).resolve())


if __name__ == "__main__":
    unittest.main()
