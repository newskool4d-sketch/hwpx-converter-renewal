import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import anyway_to_hwpx_com as converter


class FakeDocument:
    def Close(self, isDirty=False):
        return None


class FakeDocuments:
    def __init__(self):
        self.docs = []

    @property
    def Count(self):
        return len(self.docs)

    def Add(self, isTab=False):
        self.docs.append(FakeDocument())

    def Item(self, index):
        return self.docs[index]


class FakeHwp:
    def __init__(self):
        self.save_as_options = []
        self.XHwpDocuments = FakeDocuments()
        self.quit_called = False

    def SaveAs(self, output_path, format_name, option):
        self.save_as_options.append((Path(output_path).name, format_name, option))
        Path(output_path).write_bytes(b"saved")

    def Quit(self):
        self.quit_called = True


class SaveAsOptionTests(unittest.TestCase):
    def test_convert_file_uses_nonlocking_hwpx_save_option(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "sample.md"
            output = Path(tmp) / "sample.hwpx"
            source.write_text("# 제목", encoding="utf-8")
            hwp = FakeHwp()

            with (
                patch.object(converter, "detect_and_parse", return_value=[{"type": "p", "text": "본문"}]),
                patch.object(converter, "build_doc", return_value=None),
                patch.object(converter, "apply_official_page_margins", return_value=None),
                patch.object(converter, "apply_table_layout_profiles", return_value=None),
                patch.object(converter, "apply_list_hanging_indents", return_value=None),
                patch.object(converter, "fix_body_text_prid", return_value=None),
                patch.object(converter.time, "sleep", return_value=None),
            ):
                converter.convert_file(hwp, source, output)

        self.assertEqual(hwp.save_as_options, [("sample.hwpx", "HWPX", "lock:false")])

    def test_convert_file_reports_diagnose_stages_in_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "sample.md"
            output = Path(tmp) / "sample.hwpx"
            source.write_text("# 제목", encoding="utf-8")
            hwp = FakeHwp()
            stages = []

            with (
                patch.object(converter, "detect_and_parse", return_value=[{"type": "p", "text": "본문"}]),
                patch.object(converter, "build_doc", return_value=None),
                patch.object(converter, "apply_official_page_margins", return_value=None),
                patch.object(converter, "apply_table_layout_profiles", return_value=None),
                patch.object(converter, "apply_list_hanging_indents", return_value=None),
                patch.object(converter, "fix_body_text_prid", return_value=None),
                patch.object(converter.time, "sleep", return_value=None),
            ):
                converter.convert_file(hwp, source, output, diagnose_stage=stages.append)

        self.assertEqual(
            stages,
            [
                "parse_source",
                "XHwpDocuments.Add",
                "build_doc",
                "SaveAs",
                "doc.Close",
                "postprocess",
                "finalize",
            ],
        )

    def test_main_prints_diagnose_stages_when_flag_is_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "sample.md"
            source.write_text("# 제목", encoding="utf-8")
            hwp = FakeHwp()
            stdout = io.StringIO()

            with (
                contextlib.redirect_stdout(stdout),
                patch.object(converter, "create_hwp_object", return_value=hwp),
                patch.object(converter, "detect_and_parse", return_value=[{"type": "p", "text": "본문"}]),
                patch.object(converter, "build_doc", return_value=None),
                patch.object(converter, "apply_official_page_margins", return_value=None),
                patch.object(converter, "apply_table_layout_profiles", return_value=None),
                patch.object(converter, "apply_list_hanging_indents", return_value=None),
                patch.object(converter, "fix_body_text_prid", return_value=None),
                patch.object(converter.time, "sleep", return_value=None),
            ):
                exit_code = converter.main([str(source), "-o", tmp, "--diagnose-stages"])

        self.assertEqual(exit_code, 0)
        self.assertTrue(hwp.quit_called)
        self.assertIn("[diagnose] parse_source", stdout.getvalue())
        self.assertIn("[diagnose] finalize", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
