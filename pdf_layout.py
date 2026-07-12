from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math
import os
from pathlib import Path
from typing import Final

import fitz


LAYOUT_DPI: Final = 200
LAYOUT_COLOR_MODE: Final = "RGB"
MAX_LAYOUT_OUTPUT_BYTES: Final = 500 * 1024 * 1024


class PdfMode(StrEnum):
    LAYOUT = "layout"
    EDITABLE = "editable"


@dataclass(frozen=True, slots=True)
class PdfModeError(Exception):
    selected_mode: str

    def __str__(self) -> str:
        return f"Unsupported PDF mode '{self.selected_mode}'; choose 'layout' or 'editable'."


@dataclass(frozen=True, slots=True)
class PdfPageImageBlock:
    image_path: Path
    width_points: float
    height_points: float


@dataclass(frozen=True, slots=True)
class RenderedPdfLayout:
    mode: PdfMode
    dpi: int
    color_mode: str
    pages: tuple[PdfPageImageBlock, ...]


@dataclass(frozen=True, slots=True)
class PdfInputError(Exception):
    source_pdf: Path
    reason: str

    def __str__(self) -> str:
        return f"PDF layout rendering cannot read '{self.source_pdf}': {self.reason}"


@dataclass(frozen=True, slots=True)
class AssetDirectoryError(Exception):
    asset_dir: Path
    reason: str

    def __str__(self) -> str:
        return f"PDF layout asset directory '{self.asset_dir}' is unusable: {self.reason}"


@dataclass(frozen=True, slots=True)
class MixedPageGeometryError(Exception):
    source_pdf: Path

    def __str__(self) -> str:
        return (
            f"PDF layout rendering cannot preserve '{self.source_pdf}' because its pages have "
            "mixed dimensions or orientations. Use PDF mode 'editable' for this file."
        )


@dataclass(frozen=True, slots=True)
class RenderedOutputLimitError(Exception):
    output_limit_bytes: int

    def __str__(self) -> str:
        return (
            "PDF layout rendering exceeds the rendered-image limit of "
            f"{self.output_limit_bytes} bytes. Use PDF mode 'editable' or split the PDF."
        )


def parse_pdf_mode(selected_mode: str) -> PdfMode:
    try:
        return PdfMode(selected_mode)
    except ValueError as error:
        raise PdfModeError(selected_mode) from error


def render_pdf_layout(
    source_pdf: Path,
    asset_dir: Path,
    *,
    max_output_bytes: int = MAX_LAYOUT_OUTPUT_BYTES,
) -> RenderedPdfLayout:
    _validate_asset_dir(asset_dir)
    if max_output_bytes <= 0:
        raise RenderedOutputLimitError(max_output_bytes)
    if not source_pdf.is_file():
        raise PdfInputError(source_pdf, "the path is not a readable PDF file")

    try:
        with fitz.open(source_pdf) as document:
            width_points, height_points = _uniform_page_dimensions(document, source_pdf)
            encoded_pages = _render_pages(document, asset_dir, max_output_bytes)
    except (fitz.EmptyFileError, fitz.FileDataError, RuntimeError) as error:
        raise PdfInputError(source_pdf, str(error)) from error

    pages: list[PdfPageImageBlock] = []
    for output_path, png_bytes in encoded_pages:
        try:
            output_path.write_bytes(png_bytes)
        except OSError as error:
            raise AssetDirectoryError(asset_dir, str(error)) from error
        pages.append(PdfPageImageBlock(output_path, width_points, height_points))
    return RenderedPdfLayout(PdfMode.LAYOUT, LAYOUT_DPI, LAYOUT_COLOR_MODE, tuple(pages))


def _validate_asset_dir(asset_dir: Path) -> None:
    if not asset_dir.exists():
        raise AssetDirectoryError(asset_dir, "create it before rendering; the renderer never creates it")
    if not asset_dir.is_dir():
        raise AssetDirectoryError(asset_dir, "it must be an existing directory")
    mode = asset_dir.stat().st_mode
    if mode & 0o222 == 0 or not os.access(asset_dir, os.W_OK):
        raise AssetDirectoryError(asset_dir, "it must be writable by the caller")


def _uniform_page_dimensions(document: fitz.Document, source_pdf: Path) -> tuple[float, float]:
    if document.page_count == 0:
        raise PdfInputError(source_pdf, "the PDF has no pages")
    first_rect = document[0].rect
    first_width = float(first_rect.width)
    first_height = float(first_rect.height)
    first_portrait = first_height > first_width
    for page in document:
        rect = page.rect
        dimensions_match = math.isclose(rect.width, first_width, abs_tol=0.01) and math.isclose(
            rect.height, first_height, abs_tol=0.01
        )
        orientation_matches = (rect.height > rect.width) == first_portrait
        if not dimensions_match or not orientation_matches:
            raise MixedPageGeometryError(source_pdf)
    return first_width, first_height


def _render_pages(
    document: fitz.Document, asset_dir: Path, max_output_bytes: int
) -> list[tuple[Path, bytes]]:
    encoded_pages: list[tuple[Path, bytes]] = []
    rendered_bytes = 0
    for page_number, page in enumerate(document, start=1):
        output_path = asset_dir / f"page-{page_number:04d}.png"
        if output_path.exists():
            raise AssetDirectoryError(asset_dir, f"'{output_path.name}' already exists")
        pixmap = page.get_pixmap(dpi=LAYOUT_DPI, colorspace=fitz.csRGB, alpha=False)
        png_bytes = pixmap.tobytes("png")
        rendered_bytes += len(png_bytes)
        if rendered_bytes > max_output_bytes:
            raise RenderedOutputLimitError(max_output_bytes)
        encoded_pages.append((output_path, png_bytes))
    return encoded_pages

