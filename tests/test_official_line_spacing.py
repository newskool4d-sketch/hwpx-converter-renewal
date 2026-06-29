import tempfile
import unittest
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

import anyway_to_hwpx_com as converter

HH = "http://www.hancom.co.kr/hwpml/2011/head"
HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HC = "http://www.hancom.co.kr/hwpml/2011/core"
NS = {"hh": HH, "hp": HP, "hc": HC}


def write_header_hwpx(path, paraprs):
    header = (
        f'<hh:head xmlns:hh="{HH}" xmlns:hp="{HP}" xmlns:hc="{HC}">'
        f'<hh:refList><hh:paraProperties>{paraprs}</hh:paraProperties></hh:refList></hh:head>'
    )
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("Contents/header.xml", header.encode("utf-8"))
        zf.writestr("Contents/section0.xml", f'<hp:sec xmlns:hp="{HP}"/>'.encode("utf-8"))


def read_paraprs(path):
    with zipfile.ZipFile(path, "r") as zf:
        return ET.fromstring(zf.read("Contents/header.xml")).findall(".//hh:paraPr", NS)


class OfficialLineSpacingTests(unittest.TestCase):
    def test_updates_existing_line_spacing_to_160_percent(self):
        parapr = (
            '<hh:paraPr id="0"><hh:align horizontal="JUSTIFY"/>'
            '<hh:lineSpacing type="PERCENT" value="100" unit="HWPUNIT"/></hh:paraPr>'
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "h.hwpx"
            write_header_hwpx(path, parapr)
            converter.apply_official_line_spacing(path)
            ls = read_paraprs(path)[0].find("hh:lineSpacing", NS)
        self.assertEqual(ls.get("type"), "PERCENT")
        self.assertEqual(ls.get("value"), "160")

    def test_inserts_line_spacing_when_absent(self):
        parapr = (
            '<hh:paraPr id="0"><hh:align horizontal="JUSTIFY"/>'
            '<hh:heading type="NONE"/></hh:paraPr>'
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "h.hwpx"
            write_header_hwpx(path, parapr)
            converter.apply_official_line_spacing(path)
            ls = read_paraprs(path)[0].find("hh:lineSpacing", NS)
        self.assertIsNotNone(ls)
        self.assertEqual(ls.get("value"), "160")
        self.assertEqual(ls.get("type"), "PERCENT")


if __name__ == "__main__":
    unittest.main()
