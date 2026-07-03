import unittest
import xml.etree.ElementTree as ET

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
        f"<hh:paraProperties>{pp}</hh:paraProperties></hh:refList></hh:head>"
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


class HeadingParagraphSpacingTests(unittest.TestCase):
    def test_h1_exclusive_para_pr_gets_spacing(self):
        # charPr 5 = H1(1600). paraPr 1은 H1 단락에만 쓰임 → 5pt/2.5pt = 500/250
        header = _header([("0", "1300", False), ("5", "1600", False)], ["0", "1"])
        section = _section([("1", "5"), ("0", "0")])  # H1→pp1, 본문→pp0
        changed, skipped = converter._set_heading_para_spacing(header, section)
        self.assertTrue(changed)
        self.assertEqual(_prev_next(_para_pr(header, "1")), ("500", "250"))

    def test_body_para_pr_unchanged(self):
        header = _header([("0", "1300", False), ("5", "1600", False)], ["0", "1"])
        section = _section([("1", "5"), ("0", "0")])
        converter._set_heading_para_spacing(header, section)
        self.assertEqual(_prev_next(_para_pr(header, "0")), ("0", "0"))

    def test_shared_para_pr_is_skipped(self):
        # paraPr 1이 H1 단락과 본문 단락에 함께 쓰이면(공유) 적용하지 않는다
        header = _header([("0", "1300", False), ("5", "1600", False)], ["0", "1"])
        section = _section([("1", "5"), ("1", "0")])  # 둘 다 pp1
        changed, skipped = converter._set_heading_para_spacing(header, section)
        self.assertEqual(_prev_next(_para_pr(header, "1")), ("0", "0"))
        self.assertGreaterEqual(skipped, 1)

    def test_h2_and_h3_values(self):
        header = _header(
            [("0", "1300", False), ("6", "1400", False), ("8", "1300", True)],
            ["0", "2", "3"],
        )
        section = _section([("2", "6"), ("3", "8"), ("0", "0")])
        converter._set_heading_para_spacing(header, section)
        self.assertEqual(_prev_next(_para_pr(header, "2")), ("400", "200"))  # H2 4/2pt
        self.assertEqual(_prev_next(_para_pr(header, "3")), ("300", "150"))  # H3 3/1.5pt

    def test_body_1300_not_bold_is_not_heading(self):
        # 본문 13pt(1300, 굵기 없음)는 제목 아님 → 간격 미적용
        header = _header([("0", "1300", False)], ["0"])
        section = _section([("0", "0")])
        changed, skipped = converter._set_heading_para_spacing(header, section)
        self.assertEqual(_prev_next(_para_pr(header, "0")), ("0", "0"))


if __name__ == "__main__":
    unittest.main()
