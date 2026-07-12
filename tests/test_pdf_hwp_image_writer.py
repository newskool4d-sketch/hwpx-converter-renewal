from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import DEFAULT, patch

import anyway_to_hwpx_com as converter
from pdf_layout import PdfMode, PdfPageImageBlock, RenderedPdfLayout


class _FakeParameterSet:
    def __init__(self, *, item_sets: dict[str, "_FakeParameterSet"] | None = None):
        self.items: dict[str, int | float | str | bool] = {}
        self.item_sets = item_sets or {}

    def SetItem(self, name, value):
        self.items[name] = value

    def Item(self, name):
        return self.item_sets[name]

    def CreateItemSet(self, name, _type_name):
        nested = _FakeParameterSet()
        self.item_sets[name] = nested
        return nested


class _FakeAction:
    def __init__(self, name, *, execute_result=True, action_log=None):
        self.name = name
        self.execute_result = execute_result
        self.action_log = action_log if action_log is not None else []
        self.set = _FakeParameterSet(item_sets={"PageDef": _FakeParameterSet()})

    def CreateSet(self):
        return self.set

    def GetDefault(self, parameter_set):
        self.action_log.append((self.name, "GetDefault", parameter_set))

    def Execute(self, parameter_set):
        self.action_log.append((self.name, "Execute", parameter_set))
        return self.execute_result


class _FakeHAction:
    def __init__(self, *, execute_result=True, run_result=True):
        self.execute_result = execute_result
        self.run_result = run_result
        self.actions = []
        self.runs = []

    def CreateAction(self, name):
        action = _FakeAction(name, execute_result=self.execute_result, action_log=self.actions)
        self.actions.append((name, "CreateAction", action))
        return action

    def GetDefault(self, name, parameter_set):
        self.actions.append((name, "GetDefault", parameter_set))

    def Execute(self, name, parameter_set):
        self.actions.append((name, "Execute", parameter_set))
        return self.execute_result

    def Run(self, name):
        self.runs.append(name)
        return self.run_result


class _FakeHwp:
    def __init__(self, *, execute_result=True, insert_result=True, run_result=True):
        self.HAction = _FakeHAction(execute_result=execute_result, run_result=run_result)
        insert_text = type("InsertTextParameters", (), {"HSet": _FakeParameterSet(), "Text": ""})()
        self.HParameterSet = type("ParameterSets", (), {"HInsertText": insert_text})()
        self.insert_result = insert_result
        self.insert_calls = []

    def CreateAction(self, name):
        return self.HAction.CreateAction(name)

    def InsertPicture(self, *args):
        self.insert_calls.append(args)
        return self.insert_result


def _page(root: Path, name: str, width: float, height: float) -> PdfPageImageBlock:
    image = root / name
    image.write_bytes(b"png")
    return PdfPageImageBlock(image, width, height)


class PdfHwpImageWriterTests(unittest.TestCase):
    def test_page_setup_uses_nested_page_def_and_source_geometry(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            pages = (_page(root, "p1.png", 595.0, 842.0), _page(root, "p2.png", 595.0, 842.0))
            hwp = _FakeHwp()

            converter.configure_pdf_page_setup(hwp, pages)

        action = next(action for name, kind, action in hwp.HAction.actions if name == "PageSetup" and kind == "CreateAction")
        page_def = action.set.Item("PageDef")
        self.assertEqual(page_def.items["PaperWidth"], 59500)
        self.assertEqual(page_def.items["PaperHeight"], 84200)
        self.assertEqual(page_def.items["Landscape"], 0)
        for item in ("TopMargin", "BottomMargin", "LeftMargin", "RightMargin", "HeaderLen", "FooterLen", "GutterLen"):
            self.assertEqual(page_def.items[item], 0)
        self.assertEqual(action.action_log[-1][1], "Execute")

    def test_page_setup_landscape_uses_width_greater_than_height(self):
        with TemporaryDirectory() as tmp:
            pages = (_page(Path(tmp), "p1.png", 842.0, 595.0),)
            hwp = _FakeHwp()

            converter.configure_pdf_page_setup(hwp, pages)

        action = next(action for name, kind, action in hwp.HAction.actions if name == "PageSetup" and kind == "CreateAction")
        page_def = action.set.Item("PageDef")
        self.assertEqual(page_def.items["PaperWidth"], 84200)
        self.assertEqual(page_def.items["PaperHeight"], 59500)
        self.assertEqual(page_def.items["Landscape"], 1)

    def test_page_setup_false_execute_fails(self):
        with TemporaryDirectory() as tmp:
            pages = (_page(Path(tmp), "p1.png", 595.0, 842.0),)
            with self.assertRaises(RuntimeError):
                converter.configure_pdf_page_setup(_FakeHwp(execute_result=False), pages)

    def test_page_setup_exception_fails(self):
        with TemporaryDirectory() as tmp:
            pages = (_page(Path(tmp), "p1.png", 595.0, 842.0),)
            hwp = _FakeHwp()
            action = _FakeAction("PageSetup")

            def fail_execute(_parameter_set):
                raise RuntimeError("PageSetup failed")

            action.Execute = fail_execute
            hwp.CreateAction = lambda _name: action
            with self.assertRaises(RuntimeError):
                converter.configure_pdf_page_setup(hwp, pages)

    def test_image_insert_uses_mm_sizeoption_and_breaks_only_between_pages(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            pages = (_page(root, "p1.png", 595.0, 842.0), _page(root, "p2.png", 595.0, 842.0))
            hwp = _FakeHwp()

            converter.insert_pdf_page_images(hwp, pages)

        self.assertEqual(len(hwp.insert_calls), 2)
        self.assertEqual(
            hwp.insert_calls[0],
            (str(root / "p1.png"), True, 1, False, False, 0, 595.0 * 25.4 / 72, 842.0 * 25.4 / 72),
        )
        self.assertEqual(hwp.HAction.runs, ["BreakPage"])

    def test_false_insert_picture_fails_without_editable_fallback(self):
        with TemporaryDirectory() as tmp:
            page = _page(Path(tmp), "p1.png", 595.0, 842.0)
            with self.assertRaises(RuntimeError):
                converter.insert_pdf_page_image(_FakeHwp(insert_result=False), page)

    def test_insert_picture_exception_fails(self):
        with TemporaryDirectory() as tmp:
            page = _page(Path(tmp), "p1.png", 595.0, 842.0)
            hwp = _FakeHwp()
            hwp.InsertPicture = lambda *args: (_ for _ in ()).throw(RuntimeError("InsertPicture failed"))
            with self.assertRaises(RuntimeError):
                converter.insert_pdf_page_image(hwp, page)

    def test_false_break_page_fails(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            pages = (_page(root, "p1.png", 595.0, 842.0), _page(root, "p2.png", 595.0, 842.0))
            with self.assertRaises(RuntimeError):
                converter.insert_pdf_page_images(_FakeHwp(run_result=False), pages)

    def test_mixed_page_geometry_fails_before_inserting_images(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            pages = (_page(root, "p1.png", 595.0, 842.0), _page(root, "p2.png", 842.0, 595.0))
            hwp = _FakeHwp()
            with self.assertRaises(RuntimeError):
                converter.insert_pdf_page_images(hwp, pages)
            self.assertEqual(hwp.insert_calls, [])

    def test_break_page_exception_fails(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            pages = (_page(root, "p1.png", 595.0, 842.0), _page(root, "p2.png", 595.0, 842.0))
            hwp = _FakeHwp()
            hwp.HAction.Run = lambda _name: (_ for _ in ()).throw(RuntimeError("BreakPage failed"))
            with self.assertRaises(RuntimeError):
                converter.insert_pdf_page_images(hwp, pages)

    def test_editable_paragraph_defaults_are_sent_without_char_scale_or_spacing(self):
        hwp = _FakeHwp()

        converter.set_para_shape(hwp, align=0)

        action = next(action for name, kind, action in hwp.HAction.actions if name == "ParagraphShape" and kind == "CreateAction")
        values = action.set.items
        self.assertEqual(values["LineSpacingType"], 0)
        self.assertEqual(values["LineSpacing"], 160)
        self.assertEqual(values["NextSpacing"], 200)
        self.assertEqual(values["BreakNonLatinWord"], 0)
        self.assertNotIn("RatioHangul", values)
        self.assertNotIn("SpacingHangul", values)

    def test_false_character_shape_execute_fails(self):
        hwp = _FakeHwp(execute_result=False)

        with self.assertRaisesRegex(RuntimeError, "CharShape"):
            converter.set_char_shape(hwp)

    def test_false_break_paragraph_fails(self):
        hwp = _FakeHwp(run_result=False)

        with self.assertRaisesRegex(RuntimeError, "BreakPara"):
            converter.break_para(hwp)

    def test_false_insert_text_execute_fails(self):
        hwp = _FakeHwp(execute_result=False)

        with self.assertRaisesRegex(RuntimeError, "InsertText"):
            converter.insert_text(hwp, "본문")

    def test_false_table_create_execute_fails_at_creation(self):
        hwp = _FakeHwp(execute_result=False)

        with self.assertRaisesRegex(RuntimeError, "TableCreate"):
            converter.insert_table(hwp, ["항목"], [["내용"]])

    def test_layout_conversion_skips_all_six_editable_postprocessors(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.pdf"
            output = root / "source.hwpx"
            source.write_bytes(b"%PDF")
            rendered = RenderedPdfLayout(PdfMode.LAYOUT, 200, "RGB", (_page(root, "page.png", 595.0, 842.0),))
            postprocessors = (
                "apply_official_page_margins",
                "apply_table_layout_profiles",
                "apply_list_hanging_indents",
                "fix_body_text_prid",
                "apply_official_line_spacing",
                "apply_official_paragraph_spacing",
            )
            fake_hwp = _FakeHwp()
            fake_hwp.XHwpDocuments = type("Docs", (), {"Count": 0, "Add": lambda self, isTab=False: None, "Item": lambda self, index: type("Doc", (), {"Close": lambda self, isDirty=False: None})()})()
            with patch.object(converter, "render_pdf_layout", return_value=rendered), patch.object(
                converter, "detect_and_parse", return_value=rendered
            ), patch.object(converter.time, "sleep"), patch.multiple(
                converter, **{name: DEFAULT for name in postprocessors}
            ) as calls:
                fake_hwp.SaveAs = lambda path, fmt, option: Path(path).write_bytes(b"saved")
                converter.convert_file(fake_hwp, source, output, pdf_mode="layout")

        for name in postprocessors:
            calls[name].assert_not_called()


if __name__ == "__main__":
    unittest.main()
