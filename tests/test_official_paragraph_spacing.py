import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import anyway_to_hwpx_com as converter

HH = converter._NS_HH
HP = converter._NS_HP
HC = converter._NS_HC


def _margin(prev=0, nxt=0):
    return (
        f'<hp:switch xmlns:hp="{HP}"><hp:case>'
        f'<hh:margin xmlns:hh="{HH}" xmlns:hc="{HC}">'
        f'<hc:prev value="{prev}" unit="HWPUNIT"/><hc:next value="{nxt}" unit="HWPUNIT"/>'
        f'</hh:margin></hp:case></hp:switch>'
    )


def _header(charprs, paraprs):
    cp = "".join(
        f'<hh:charPr id="{cid}" height="{h}">{"<hh:bold/>" if bold else ""}</hh:charPr>'
        for cid, h, bold in charprs
    )
    pp = "".join(f'<hh:paraPr id="{pid}">{_margin()}</hh:paraPr>' for pid in paraprs)
    return ET.fromstring(
        f'<hh:head xmlns:hh="{HH}" xmlns:hp="{HP}" xmlns:hc="{HC}">'
        f"<hh:refList><hh:charProperties>{cp}</hh:charProperties>"
        f'<hh:paraProperties itemCnt="{len(paraprs)}">{pp}</hh:paraProperties></hh:refList></hh:head>'
    )


def _section(paras):
    body = "".join(
        f'<hp:p paraPrIDRef="{ppid}"><hp:run charPrIDRef="{cid}"><hp:t>x</hp:t></hp:run></hp:p>'
        for ppid, cid in paras
    )
    return ET.fromstring(f'<hp:sec xmlns:hp="{HP}">{body}</hp:sec>')


def _prev_next(para_pr):
    margin = para_pr.find(f".//{{{HH}}}margin")
    prev = margin.find(f"{{{HC}}}prev")
    nxt = margin.find(f"{{{HC}}}next")
    return prev.get("value"), nxt.get("value")


def _para_pr(header_root, pid):
    for e in header_root.iter(f"{{{HH}}}paraPr"):
        if e.get("id") == pid:
            return e
    return None


def _ref_of(section_root, charid):
    """주어진 charPrIDRef 런을 가진 단락의 paraPrIDRef."""
    for p in section_root.iter(f"{{{HP}}}p"):
        run = p.find(f".//{{{HP}}}run")
        if run is not None and run.get("charPrIDRef") == charid:
            return p.get("paraPrIDRef")
    return None


def _itemcnt(header_root):
    return int(header_root.find(f".//{{{HH}}}paraProperties").get("itemCnt"))


class ExclusiveHeadingSpacingTests(unittest.TestCase):
    def test_h1_exclusive_para_pr_set_in_place(self):
        header = _header([("0", "1300", False), ("5", "1600", False)], ["0", "1"])
        section = _section([("1", "5"), ("0", "0")])  # pp1 = H1 전용
        changed, cloned = converter._set_heading_para_spacing(header, section)
        self.assertTrue(changed)
        self.assertEqual(cloned, 0)
        self.assertEqual(_ref_of(section, "5"), "1")  # 제자리
        self.assertEqual(_prev_next(_para_pr(header, "1")), ("500", "250"))

    def test_body_para_pr_unchanged(self):
        header = _header([("0", "1300", False), ("5", "1600", False)], ["0", "1"])
        section = _section([("1", "5"), ("0", "0")])
        converter._set_heading_para_spacing(header, section)
        self.assertEqual(_prev_next(_para_pr(header, "0")), ("0", "0"))

    def test_h2_and_h3_exclusive_values(self):
        header = _header(
            [("0", "1300", False), ("6", "1400", False), ("8", "1300", True)],
            ["0", "2", "3"],
        )
        section = _section([("2", "6"), ("3", "8"), ("0", "0")])
        converter._set_heading_para_spacing(header, section)
        self.assertEqual(_prev_next(_para_pr(header, "2")), ("400", "200"))
        self.assertEqual(_prev_next(_para_pr(header, "3")), ("300", "150"))

    def test_body_1300_not_bold_is_not_heading(self):
        header = _header([("0", "1300", False)], ["0"])
        section = _section([("0", "0")])
        changed, cloned = converter._set_heading_para_spacing(header, section)
        self.assertEqual(_prev_next(_para_pr(header, "0")), ("0", "0"))


class SharedHeadingSpacingCloneTests(unittest.TestCase):
    """제목이 본문과 paraPr을 공유하면 clone 후 제목에만 재배정한다."""

    def test_shared_para_pr_is_cloned_and_reassigned(self):
        header = _header([("0", "1300", False), ("5", "1600", False)], ["0", "1"])
        section = _section([("1", "5"), ("1", "0")])  # H1·본문 모두 pp1(공유)
        changed, cloned = converter._set_heading_para_spacing(header, section)
        self.assertTrue(changed)
        self.assertGreaterEqual(cloned, 1)
        new_ref = _ref_of(section, "5")
        self.assertNotEqual(new_ref, "1")  # 제목은 새 paraPr로 이동
        self.assertEqual(_prev_next(_para_pr(header, new_ref)), ("500", "250"))
        self.assertEqual(_ref_of(section, "0"), "1")  # 본문은 그대로
        self.assertEqual(_prev_next(_para_pr(header, "1")), ("0", "0"))  # 원본 0/0

    def test_itemcnt_incremented_on_clone(self):
        header = _header([("0", "1300", False), ("5", "1600", False)], ["0", "1"])
        section = _section([("1", "5"), ("1", "0")])
        before = _itemcnt(header)
        converter._set_heading_para_spacing(header, section)
        self.assertEqual(_itemcnt(header), before + 1)

    def test_multi_level_shared_clones_each_level(self):
        # pp0을 H1·H3·본문이 공유 → H1/H3 각각 별도 clone, 본문은 원본 유지
        header = _header(
            [("0", "1300", False), ("5", "1600", False), ("8", "1300", True)],
            ["0"],
        )
        section = _section([("0", "5"), ("0", "8"), ("0", "0")])
        changed, cloned = converter._set_heading_para_spacing(header, section)
        h1ref, h3ref, bodyref = _ref_of(section, "5"), _ref_of(section, "8"), _ref_of(section, "0")
        self.assertEqual(cloned, 2)
        self.assertEqual(bodyref, "0")
        self.assertNotIn(h1ref, ("0", None))
        self.assertNotEqual(h1ref, h3ref)
        self.assertEqual(_prev_next(_para_pr(header, h1ref)), ("500", "250"))
        self.assertEqual(_prev_next(_para_pr(header, h3ref)), ("300", "150"))
        self.assertEqual(_prev_next(_para_pr(header, "0")), ("0", "0"))

    def test_new_paraPr_ids_are_unique(self):
        header = _header([("0", "1300", False), ("5", "1600", False)], ["0", "1"])
        section = _section([("1", "5"), ("1", "0")])
        converter._set_heading_para_spacing(header, section)
        ids = [e.get("id") for e in header.iter(f"{{{HH}}}paraPr")]
        self.assertEqual(len(ids), len(set(ids)))


class ParagraphSpacingFileRoundTripTests(unittest.TestCase):
    """파일 라운드트립: clone·재배정이 실제 .hwpx(section0.xml)에 기록되는가."""

    def _write_hwpx(self, tmp):
        # 실제 HWPX처럼 hh/hp/hc 정규 프리픽스로 직렬화(ns0 예약 프리픽스 회피)
        ET.register_namespace("hh", HH)
        ET.register_namespace("hp", HP)
        ET.register_namespace("hc", HC)
        header = _header([("0", "1300", False), ("5", "1600", False)], ["0"])
        section = _section([("0", "5"), ("0", "0")])  # 제목·본문 모두 pp0(공유)
        path = Path(tmp) / "t.hwpx"
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("Contents/header.xml", ET.tostring(header, encoding="unicode"))
            z.writestr("Contents/section0.xml", ET.tostring(section, encoding="unicode"))
        return path

    def test_clone_reassignment_persisted_to_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_hwpx(tmp)
            converter.apply_official_paragraph_spacing(path)
            with zipfile.ZipFile(path) as z:
                sroot = ET.fromstring(z.read("Contents/section0.xml"))
                hroot = ET.fromstring(z.read("Contents/header.xml"))
        ref = _ref_of(sroot, "5")  # 제목 단락의 paraPrIDRef
        self.assertNotEqual(ref, "0")  # clone으로 재배정돼 파일에 기록됨
        self.assertEqual(_prev_next(_para_pr(hroot, ref)), ("500", "250"))
        self.assertEqual(_ref_of(sroot, "0"), "0")  # 본문은 그대로


if __name__ == "__main__":
    unittest.main()
