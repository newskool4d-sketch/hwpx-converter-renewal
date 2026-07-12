from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import argparse
import contextlib
import io
import unittest
from types import SimpleNamespace
from unittest.mock import DEFAULT, patch

import anyway_to_hwpx_com as converter
from pdf_layout import PdfMode, PdfPageImageBlock, RenderedPdfLayout


class _FakeDocument:
    def __init__(self):
        self.close_calls = []

    def Close(self, isDirty=False):
        self.close_calls.append(isDirty)
        return None


class _FakeDocuments:
    def __init__(self):
        self.docs = []

    @property
    def Count(self):
        return len(self.docs)

    def Add(self, isTab=False):
        self.docs.append(_FakeDocument())

    def Item(self, index):
        return self.docs[index]


class _FakeHwp:
    def __init__(self, save_failure=None):
        self.XHwpDocuments = _FakeDocuments()
        self.save_failure = save_failure
        self.image_paths_during_save = []

    def SaveAs(self, output_path, format_name, option):
        if self.save_failure is not None:
            raise self.save_failure
        Path(output_path).write_bytes(b"saved")


class PdfModeWiringTests(unittest.TestCase):
    def test_characterization_detect_and_parse_passes_kordoc_home_to_pdf_parser(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.pdf"
            source.write_bytes(b"%PDF")
            with patch.object(converter, "parse_pdf", return_value=[{"type": "p", "text": "ok"}]) as parse:
                result = converter.detect_and_parse(source, kordoc_home="C:/kordoc")

        self.assertEqual(result, [{"type": "p", "text": "ok"}])
        parse.assert_called_once_with(source, kordoc_home="C:/kordoc", pdf_mode="layout", asset_dir=None)

    def test_characterization_editable_parser_keeps_odl_then_pdfplumber_order(self):
        calls = []

        def odl(path):
            calls.append("odl")
            raise RuntimeError("java unavailable")

        def plumber(path):
            calls.append("pdfplumber")
            return [{"type": "p", "text": "structured"}]

        with patch.object(converter, "extract_pdf_blocks_odl", side_effect=odl), patch.object(
            converter, "extract_pdf_blocks_pdfplumber", side_effect=plumber
        ), patch.object(converter, "try_kordoc_pdf_text") as kordoc:
            result = converter.parse_pdf(Path("source.pdf"), pdf_mode="editable")

        self.assertEqual(result, [{"type": "p", "text": "structured"}])
        self.assertEqual(calls, ["odl", "pdfplumber"])
        kordoc.assert_not_called()

    def test_cli_exposes_layout_as_the_default_pdf_mode(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            converter.main(["--help"])

        self.assertEqual(raised.exception.code, 0)
        help_text = output.getvalue()
        self.assertIn("--pdf-mode {layout,editable}", help_text)
        self.assertIn("default: layout", help_text)

    def test_layout_parse_bypasses_text_extractors_and_receives_caller_asset_directory(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.pdf"
            asset_dir = root / "assets"
            source.write_bytes(b"%PDF")
            asset_dir.mkdir()
            rendered = RenderedPdfLayout(
                PdfMode.LAYOUT,
                200,
                "RGB",
                (PdfPageImageBlock(asset_dir / "page-0001.png", 595.0, 842.0),),
            )
            with patch.object(converter, "render_pdf_layout", return_value=rendered) as render, patch.object(
                converter, "extract_pdf_blocks_odl", side_effect=AssertionError("text path used")
            ), patch.object(converter, "extract_pdf_blocks_pdfplumber", side_effect=AssertionError("text path used")):
                result = converter.parse_pdf(source, pdf_mode="layout", asset_dir=asset_dir)

        self.assertIs(result, rendered)
        render.assert_called_once_with(source, asset_dir)

    def test_layout_conversion_keeps_images_until_save_and_cleans_assets_after_success(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.pdf"
            output = root / "source.hwpx"
            source.write_bytes(b"%PDF")
            hwp = _FakeHwp()
            observed = []

            def fake_insert(hwp_obj, page):
                observed.append(page.image_path.is_file())

            def fake_save(output_path, format_name, option):
                observed.append(all(observed))
                Path(output_path).write_bytes(b"saved")

            hwp.SaveAs = fake_save
            with patch.object(converter, "render_pdf_layout", side_effect=lambda path, asset_dir: _render_fake_page(asset_dir)), patch.object(
                converter, "insert_pdf_page_image", side_effect=fake_insert
            ), patch.object(converter.time, "sleep", return_value=None):
                converter.convert_file(hwp, source, output, pdf_mode="layout")

            self.assertEqual(observed, [True, True])
            self.assertTrue(output.is_file())
            self.assertEqual(list(root.glob("anyway-to-hwpx-pdf-*")), [])

    def test_layout_build_failure_wraps_context_and_cleans_assets(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.pdf"
            output = root / "source.hwpx"
            source.write_bytes(b"%PDF")
            hwp = _FakeHwp()
            with patch.object(converter, "render_pdf_layout", side_effect=lambda path, asset_dir: _render_fake_page(asset_dir)), patch.object(
                converter, "insert_pdf_page_image", side_effect=RuntimeError("insert failed")
            ), patch.object(converter.time, "sleep", return_value=None):
                with self.assertRaises(RuntimeError) as raised:
                    converter.convert_file(hwp, source, output, pdf_mode="layout")

            self.assertIn("build", str(raised.exception).lower())
            self.assertIn("source.pdf", str(raised.exception))
            self.assertEqual(list(root.glob("anyway-to-hwpx-pdf-*")), [])

    def test_layout_build_failure_closes_created_document_once(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.pdf"
            output = root / "source.hwpx"
            source.write_bytes(b"%PDF")
            hwp = _FakeHwp()
            with patch.object(converter, "render_pdf_layout", side_effect=lambda path, asset_dir: _render_fake_page(asset_dir)), patch.object(
                converter, "insert_pdf_page_image", side_effect=RuntimeError("insert failed")
            ), patch.object(converter.time, "sleep", return_value=None):
                with self.assertRaises(RuntimeError):
                    converter.convert_file(hwp, source, output, pdf_mode="layout")

            self.assertEqual(hwp.XHwpDocuments.docs[0].close_calls, [False])

    def test_layout_save_failure_wraps_context_and_cleans_assets(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.pdf"
            output = root / "source.hwpx"
            source.write_bytes(b"%PDF")
            hwp = _FakeHwp(save_failure=RuntimeError("save failed"))
            with patch.object(converter, "render_pdf_layout", side_effect=lambda path, asset_dir: _render_fake_page(asset_dir)), patch.object(
                converter, "insert_pdf_page_image"
            ), patch.object(converter.time, "sleep", return_value=None):
                with self.assertRaises(RuntimeError) as raised:
                    converter.convert_file(hwp, source, output, pdf_mode="layout")

            self.assertIn("save", str(raised.exception).lower())
            self.assertIn("source.pdf", str(raised.exception))
            self.assertEqual(list(root.glob("anyway-to-hwpx-pdf-*")), [])

    def test_layout_oserror_build_failure_wraps_context_and_cleans_assets(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.pdf"
            output = root / "source.hwpx"
            source.write_bytes(b"%PDF")
            with patch.object(converter, "render_pdf_layout", side_effect=lambda path, asset_dir: _render_fake_page(asset_dir)), patch.object(
                converter, "insert_pdf_page_image", side_effect=FileNotFoundError("page missing")
            ), patch.object(converter.time, "sleep", return_value=None):
                with self.assertRaises(RuntimeError) as raised:
                    converter.convert_file(_FakeHwp(), source, output, pdf_mode="layout")

            self.assertIn("build", str(raised.exception).lower())
            self.assertIn("source.pdf", str(raised.exception))
            self.assertIsInstance(raised.exception.__cause__, FileNotFoundError)
            self.assertEqual(list(root.glob("anyway-to-hwpx-pdf-*")), [])

    def test_invalid_pdf_mode_is_rejected_without_global_state(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.pdf"
            output = Path(tmp) / "source.hwpx"
            source.write_bytes(b"%PDF")

            with self.assertRaises(Exception) as raised:
                converter.convert_file(_FakeHwp(), source, output, pdf_mode="reflow")

        self.assertIn("layout", str(raised.exception))
        self.assertIn("editable", str(raised.exception))

    def test_layout_conversion_skips_all_editable_postprocessors(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.pdf"
            output = root / "source.hwpx"
            source.write_bytes(b"%PDF")
            postprocessors = (
                "apply_official_page_margins",
                "apply_table_layout_profiles",
                "apply_list_hanging_indents",
                "fix_body_text_prid",
                "apply_official_line_spacing",
                "apply_official_paragraph_spacing",
            )
            with patch.object(converter, "render_pdf_layout", side_effect=lambda path, asset_dir: _render_fake_page(asset_dir)), patch.object(
                converter, "insert_pdf_page_image"
            ) as insert, patch.object(converter.time, "sleep", return_value=None):
                with patch.multiple(converter, **{name: DEFAULT for name in postprocessors}) as calls:
                    converter.convert_file(_FakeHwp(), source, output, pdf_mode="layout")

            insert.assert_called_once()
            for name in postprocessors:
                calls[name].assert_not_called()

    def test_none_capability_rejects_pdf_before_rendering(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.pdf"
            source.write_bytes(b"%PDF")
            with patch.object(converter, "detect_capabilities", return_value=SimpleNamespace(pdf_enabled=False)), patch.object(
                converter, "parse_pdf", side_effect=AssertionError("renderer used")
            ):
                with self.assertRaises(RuntimeError) as raised:
                    converter.detect_and_parse(source, pdf_mode="layout", asset_dir=Path(tmp))

        self.assertIn("PDF input is unavailable", str(raised.exception))

    def test_editable_pdf_reports_java_fallback_note_when_odl_is_unavailable(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.pdf"
            source.write_bytes(b"%PDF")
            capabilities = SimpleNamespace(pdf_enabled=True, odl_enabled=False, java_major=8)
            with patch.object(converter, "detect_capabilities", return_value=capabilities), patch.object(
                converter, "parse_pdf", return_value=[{"type": "p", "text": "fallback"}]
            ):
                result = converter.detect_and_parse(source, pdf_mode="editable")
                notes = converter.pop_conversion_notes()

        self.assertEqual(result, [{"type": "p", "text": "fallback"}])
        self.assertEqual(len(notes), 1)
        self.assertIn("Java 8", notes[0])
        self.assertIn("fallback", notes[0])


def _render_fake_page(asset_dir: Path) -> RenderedPdfLayout:
    image_path = asset_dir / "page-0001.png"
    image_path.write_bytes(b"png")
    return RenderedPdfLayout(
        PdfMode.LAYOUT,
        200,
        "RGB",
        (PdfPageImageBlock(image_path, 595.0, 842.0),),
    )


if __name__ == "__main__":
    unittest.main()
