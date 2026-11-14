"""신뢰할 수 없는 입력과 중단된 작업에 대한 방어 회귀."""
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import anyway_to_hwpx_com as converter
import conversion_process
import kordoc_client
from table_grid import MAX_TABLE_CELLS, SourceCell, expand_spanned_rows

# 1x1 PNG
_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6360606060000000050001a5f645400000000049454e44ae426082"
)


class TableSizeLimitTests(unittest.TestCase):
    def test_huge_html_span_is_clamped_quickly(self):
        started = time.monotonic()
        block = converter.parse_html(
            "<table><tr><td rowspan='1000000' colspan='1000'>제목</td><td>옆</td></tr>"
            "<tr><td>아래</td></tr></table>"
        )[0]
        self.assertLess(time.monotonic() - started, 3)
        self.assertEqual(len(block["rows"]), 1)
        self.assertIn("옆", block["header"])

    def test_malformed_span_values_do_not_fail_the_conversion(self):
        block = converter.parse_html(
            "<table><tr><td rowspan='2;'>A</td><td colspan='100%'>B</td></tr><tr><td>C</td></tr></table>"
        )[0]
        self.assertEqual(block["header"][0], "A")

    def test_rowspan_beyond_table_makes_no_ghost_rows(self):
        grid, merges = expand_spanned_rows([[SourceCell("A", 5, 1), SourceCell("b1")], [SourceCell("b2")]])
        self.assertEqual(grid, [["A", "b1"], ["", "b2"]])
        self.assertEqual(merges, [[0, 0, 2, 1]])

    def test_oversized_grid_is_rejected(self):
        rows = [[SourceCell("x", 1, 1000)] for _ in range(MAX_TABLE_CELLS // 1000 + 1)]
        with self.assertRaises(ValueError):
            expand_spanned_rows(rows)

    def test_xlsx_formatting_far_away_does_not_inflate_the_table(self):
        from openpyxl import Workbook
        from openpyxl.styles import Font

        workbook = Workbook()
        sheet = workbook.active
        sheet["A1"], sheet["B1"] = "구분", "금액"
        sheet["A2"], sheet["B2"] = "강사료", 100
        sheet.cell(row=50000, column=30).font = Font(bold=True)
        started = time.monotonic()
        block = converter._xlsx_table_block(sheet)
        self.assertLess(time.monotonic() - started, 3)
        self.assertEqual([block["header"]] + block["rows"], [["구분", "금액"], ["강사료", "100"]])


class MarkdownImagePathTests(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        root = Path(self._temp.name)
        self.doc_dir = root / "문서"
        (self.doc_dir / "그림").mkdir(parents=True)
        (self.doc_dir / "그림" / "inside.png").write_bytes(_PNG)
        self.outside = root / "outside.png"
        self.outside.write_bytes(_PNG)
        converter._conversion_notes.clear()

    def test_image_inside_document_folder_is_used(self):
        block = converter._markdown_image_block("그림/inside.png", self.doc_dir)
        self.assertEqual(block["type"], "image")

    def test_paths_outside_document_folder_are_refused_with_a_note(self):
        for target in (
            str(self.outside),
            self.outside.as_posix(),
            "../outside.png",
            "그림/../../outside.png",
            "/\\server\\share\\a.png",
            "//server/share/a.png",
            "\\\\server\\share\\a.png",
            "file:///C:/a.png",
            "~/a.png",
        ):
            with self.subTest(target=target):
                self.assertIsNone(converter._markdown_image_block(target, self.doc_dir))
        self.assertTrue(any("문서 폴더 밖" in note for note in converter.pop_conversion_notes()))


class EnvironmentPathTests(unittest.TestCase):
    def test_no_personal_default_path_for_legacy_ocr(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("KORDOC_HOME", None)
            os.environ.pop("KORDOC_AI_HOME", None)
            self.assertIsNone(converter.resolve_kordoc_dir())

    def test_node_is_not_taken_from_the_current_folder(self):
        with tempfile.TemporaryDirectory() as planted, tempfile.TemporaryDirectory() as real:
            name = "node.exe" if os.name == "nt" else "node"
            (Path(planted) / name).write_bytes(b"")
            (Path(real) / name).write_bytes(b"")
            previous = os.getcwd()
            os.chdir(planted)
            try:
                with patch.dict(os.environ, {"PATH": os.pathsep.join(["", ".", real])}):
                    self.assertEqual(kordoc_client._node_on_path(), str(Path(real) / name))
                with patch.dict(os.environ, {"PATH": os.pathsep.join(["", "."])}):
                    self.assertIsNone(kordoc_client._node_on_path())
            finally:
                os.chdir(previous)


class StaleTempFolderTests(unittest.TestCase):
    def test_leftover_app_temp_folders_do_not_block_emptying(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir) / "out"
            converter.prepare_output_dir(out_dir, empty_output_folder=True)
            for name in (".conversion-abc", "anyway-to-hwpx-pdf-xyz"):
                (out_dir / name).mkdir()
                (out_dir / name / "page.png").write_bytes(b"x")
            converter.prepare_output_dir(out_dir, empty_output_folder=True)
            self.assertEqual([child.name for child in out_dir.iterdir()], [converter.OUTPUT_MANIFEST_NAME])

    def test_unknown_folders_still_block_emptying(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir) / "out"
            converter.prepare_output_dir(out_dir, empty_output_folder=True)
            (out_dir / "내 자료").mkdir()
            with self.assertRaises(RuntimeError):
                converter.prepare_output_dir(out_dir, empty_output_folder=True)


@unittest.skipUnless(os.name == "nt", "Windows 프로세스 식별 전용")
class OwnedProcessTerminationTests(unittest.TestCase):
    def _child(self):
        process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        self.addCleanup(lambda: (process.kill(), process.wait()))
        for _ in range(50):
            identity = conversion_process._process_identity(process.pid)
            if identity:
                return process, identity
            time.sleep(0.05)
        self.fail("자식 프로세스를 식별하지 못함")

    def test_a_process_that_is_not_hancom_is_never_terminated(self):
        process, identity = self._child()
        self.assertFalse(conversion_process._terminate_owned_hwp((process.pid, identity[1])))
        self.assertIsNone(process.poll())

    def test_matching_name_and_start_time_is_terminated(self):
        process, identity = self._child()
        with patch.object(conversion_process, "_HWP_IMAGE_NAME", identity[0]):
            self.assertFalse(conversion_process._terminate_owned_hwp((process.pid, identity[1] + 1)))
            self.assertIsNone(process.poll())
            self.assertTrue(conversion_process._terminate_owned_hwp((process.pid, identity[1])))
        process.wait(timeout=5)

    def test_preexisting_process_is_not_claimed_as_owned(self):
        process, identity = self._child()

        class Window:
            WindowHandle = 0

        class Hwp:
            class XHwpWindows:
                @staticmethod
                def Item(_index):
                    return Window

        with patch.object(conversion_process, "_HWP_IMAGE_NAME", identity[0]), patch(
            "win32process.GetWindowThreadProcessId", return_value=(0, process.pid)
        ):
            self.assertIsNone(conversion_process._owned_hwp_process(Hwp, {process.pid}))
            self.assertEqual(conversion_process._owned_hwp_process(Hwp, set()), (process.pid, identity[1]))


if __name__ == "__main__":
    unittest.main()
