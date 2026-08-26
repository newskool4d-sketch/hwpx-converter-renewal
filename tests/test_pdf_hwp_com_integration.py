from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import os
import unittest
import xml.etree.ElementTree as ET
import zipfile

import fitz

import anyway_to_hwpx_com as converter


def _local_name(tag: str) -> str:
    return tag.rsplit('}', 1)[-1]


def _nonwhite_bounds(pixmap: fitz.Pixmap) -> tuple[int, int, int, int]:
    samples = pixmap.samples
    width, height, channels = pixmap.width, pixmap.height, pixmap.n
    points = []
    for y in range(height):
        for x in range(width):
            offset = (y * width + x) * channels
            if any(samples[offset + channel] < 245 for channel in range(min(channels, 3))):
                points.append((x, y))
    if not points:
        return (0, 0, 0, 0)
    xs, ys = zip(*points)
    return min(xs), min(ys), max(xs), max(ys)


@unittest.skipUnless(os.environ.get('HWPX_RUN_COM_TESTS') == '1', 'set HWPX_RUN_COM_TESTS=1 to run native HWP COM checks')
class PdfHwpComIntegrationTests(unittest.TestCase):
    def test_generated_pdf_round_trips_through_hwp_image_pages(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_pdf = root / 'source.pdf'
            hwpx = root / 'source.hwpx'
            roundtrip_pdf = root / 'roundtrip.pdf'
            self._write_fixture_pdf(source_pdf)
            hwp = converter.create_hwp_object(visible=False)
            try:
                converter.convert_file(hwp, source_pdf, hwpx, pdf_mode='layout')
                self._assert_hwpx_image_contract(hwpx)
                hwp.Open(str(hwpx), 'HWPX', '')
                self.assertTrue(hwp.SaveAs(str(roundtrip_pdf), 'PDF', ''))
            finally:
                hwp.Quit()
            self._assert_roundtrip(source_pdf, roundtrip_pdf)

    @staticmethod
    def _write_fixture_pdf(path: Path) -> None:
        document = fitz.open()
        try:
            page = document.new_page(width=595, height=842)
            page.draw_rect(fitz.Rect(72, 120, 520, 300), color=(0, 0, 0), fill=(0.95, 0.95, 0.95), width=2)
            page.insert_text((100, 180), 'PDF layout fixture', fontsize=18, color=(0, 0, 0))
            document.save(path)
        finally:
            document.close()

    @staticmethod
    def _assert_hwpx_image_contract(path: Path) -> None:
        with zipfile.ZipFile(path) as archive:
            sections = [name for name in archive.namelist() if name.startswith('Contents/section') and name.endswith('.xml')]
            root = ET.fromstring(archive.read(sections[0]))
        pictures = [element for element in root.iter() if _local_name(element.tag) == 'pic']
        page_pr = next((element for element in root.iter() if _local_name(element.tag) == 'pagePr'), None)
        assert page_pr is not None
        assert page_pr.get('width') or page_pr.get('height') or page_pr.find('.//*') is not None
        assert len(pictures) == len(sections)
        for picture in pictures:
            names = {_local_name(child.tag) for child in picture.iter()}
            assert {'orgSz', 'curSz', 'sz'} <= names

    @staticmethod
    def _assert_roundtrip(source: Path, roundtrip: Path) -> None:
        with fitz.open(source) as original, fitz.open(roundtrip) as exported:
            assert original.page_count == exported.page_count
            for source_page, output_page in zip(original, exported):
                source_pix = source_page.get_pixmap(colorspace=fitz.csRGB, alpha=False)
                output_pix = output_page.get_pixmap(colorspace=fitz.csRGB, alpha=False)
                assert abs(source_pix.width - output_pix.width) <= 2
                assert abs(source_pix.height - output_pix.height) <= 2
                source_bounds = _nonwhite_bounds(source_pix)
                output_bounds = _nonwhite_bounds(output_pix)
                assert all(abs(left - right) <= 2 for left, right in zip(source_bounds, output_bounds))
                count = min(len(source_pix.samples), len(output_pix.samples))
                error = sum(abs(source_pix.samples[index] - output_pix.samples[index]) for index in range(count)) / (count * 255)
                assert error <= 0.05


if __name__ == '__main__':
    unittest.main()
