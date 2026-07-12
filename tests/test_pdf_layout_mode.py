from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import fitz

from pdf_layout import (
    AssetDirectoryError,
    MixedPageGeometryError,
    PdfInputError,
    PdfMode,
    PdfModeError,
    RenderedOutputLimitError,
    parse_pdf_mode,
    render_pdf_layout,
)


class PdfLayoutModeTests(unittest.TestCase):
    def test_render_pdf_layout_reports_a_malformed_pdf_without_creating_assets(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_pdf = root / "malformed.pdf"
            asset_dir = root / "layout-assets"
            asset_dir.mkdir()
            source_pdf.write_bytes(b"not a PDF")

            with self.assertRaises(PdfInputError) as captured_error:
                render_pdf_layout(source_pdf, asset_dir)

            self.assertEqual(list(asset_dir.iterdir()), [])
            self.assertIn("cannot read", str(captured_error.exception))

    def test_render_pdf_layout_leaves_caller_owned_assets_until_the_caller_cleans_up(self) -> None:
        temporary_directory = TemporaryDirectory()
        root = Path(temporary_directory.name)
        try:
            source_pdf = root / "source.pdf"
            asset_dir = root / "layout-assets"
            asset_dir.mkdir()
            with fitz.open() as document:
                document.new_page(width=595, height=842)
                document.save(source_pdf)

            rendered = render_pdf_layout(source_pdf, asset_dir)

            self.assertTrue(root.is_dir())
            self.assertTrue(rendered.pages[0].image_path.is_file())
        finally:
            temporary_directory.cleanup()

        self.assertFalse(root.exists())

    def test_render_pdf_layout_requires_a_caller_created_asset_directory(self) -> None:
        # Given: a valid PDF and an asset directory the caller did not create.
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_pdf = root / "source.pdf"
            asset_dir = root / "missing-assets"
            with fitz.open() as document:
                document.new_page(width=595, height=842)
                document.save(source_pdf)

            # When: layout rendering receives the missing directory.
            with self.assertRaises(AssetDirectoryError) as captured_error:
                render_pdf_layout(source_pdf, asset_dir)

            # Then: it does not create the directory and tells the caller what to do.
            self.assertFalse(asset_dir.exists())
            self.assertIn("create it", str(captured_error.exception))

    def test_render_pdf_layout_rejects_a_nonwritable_asset_directory(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_pdf = root / "source.pdf"
            asset_dir = root / "readonly-assets"
            asset_dir.mkdir()
            with fitz.open() as document:
                document.new_page(width=595, height=842)
                document.save(source_pdf)
            asset_dir.chmod(0o555)
            try:
                with self.assertRaises(AssetDirectoryError) as captured_error:
                    render_pdf_layout(source_pdf, asset_dir)
            finally:
                asset_dir.chmod(0o755)

            self.assertEqual(list(asset_dir.iterdir()), [])
            self.assertIn("writable", str(captured_error.exception))

    def test_render_pdf_layout_rejects_output_beyond_the_configured_cap_before_writing(self) -> None:
        # Given: a normal A4 page but a deliberately tiny caller cap.
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_pdf = root / "large-output.pdf"
            asset_dir = root / "layout-assets"
            asset_dir.mkdir()
            with fitz.open() as document:
                document.new_page(width=595, height=842)
                document.save(source_pdf)

            # When: the page PNG would exceed the rendered-output cap.
            with self.assertRaises(RenderedOutputLimitError) as captured_error:
                render_pdf_layout(source_pdf, asset_dir, max_output_bytes=1)

            # Then: no partial page asset is persisted and editable is actionable.
            self.assertEqual(list(asset_dir.iterdir()), [])
            self.assertIn("editable", str(captured_error.exception))

    def test_render_pdf_layout_rejects_mixed_page_orientations_before_writing_assets(self) -> None:
        # Given: a PDF that mixes A4 portrait and landscape pages.
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_pdf = root / "mixed.pdf"
            asset_dir = root / "layout-assets"
            asset_dir.mkdir()
            with fitz.open() as document:
                document.new_page(width=595, height=842)
                document.new_page(width=842, height=595)
                document.save(source_pdf)

            # When: layout rendering validates the document geometry.
            with self.assertRaises(MixedPageGeometryError) as captured_error:
                render_pdf_layout(source_pdf, asset_dir)

            # Then: no assets are written and editable mode is actionable guidance.
            self.assertEqual(list(asset_dir.iterdir()), [])
            self.assertIn("editable", str(captured_error.exception))

    def test_parse_pdf_mode_explains_an_unsupported_selection(self) -> None:
        # Given: a mode outside the public contract.
        selected_mode = "reflow"

        # When: the public mode boundary parses it.
        with self.assertRaises(PdfModeError) as captured_error:
            parse_pdf_mode(selected_mode)

        # Then: callers receive the supported mode guidance.
        self.assertIn("layout", str(captured_error.exception))
        self.assertIn("editable", str(captured_error.exception))

    def test_parse_pdf_mode_returns_editable_mode(self) -> None:
        # Given: a caller-selected editable mode.
        selected_mode = "editable"

        # When: the public mode boundary parses it.
        parsed_mode = parse_pdf_mode(selected_mode)

        # Then: the strongly typed editable mode is returned.
        self.assertEqual(parsed_mode, PdfMode.EDITABLE)

    def test_render_pdf_layout_returns_a4_rgb_page_images_at_200_dpi(self) -> None:
        # Given: a two-page A4 PDF and a caller-owned asset directory.
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_pdf = root / "source.pdf"
            asset_dir = root / "layout-assets"
            asset_dir.mkdir()
            with fitz.open() as document:
                a4 = fitz.Rect(0, 0, 595, 842)
                document.new_page(width=a4.width, height=a4.height)
                document.new_page(width=a4.width, height=a4.height)
                document.save(source_pdf)

            # When: layout rendering is requested.
            rendered = render_pdf_layout(source_pdf, asset_dir)

            # Then: caller-visible blocks describe 200 DPI RGB A4 images.
            self.assertEqual(rendered.mode, PdfMode.LAYOUT)
            self.assertEqual(rendered.dpi, 200)
            self.assertEqual(rendered.color_mode, "RGB")
            self.assertEqual(len(rendered.pages), 2)
            for page in rendered.pages:
                self.assertEqual(page.width_points, 595.0)
                self.assertEqual(page.height_points, 842.0)
                self.assertEqual(page.image_path.parent, asset_dir)
                self.assertTrue(page.image_path.is_file())
                image = fitz.Pixmap(page.image_path)
                self.assertEqual(image.n, 3)
                self.assertEqual(image.alpha, 0)
                self.assertEqual(image.width, round(595 / 72 * 200))
                self.assertEqual(image.height, round(842 / 72 * 200))
            self.assertEqual(set(root.iterdir()), {source_pdf, asset_dir})


if __name__ == "__main__":
    unittest.main()
