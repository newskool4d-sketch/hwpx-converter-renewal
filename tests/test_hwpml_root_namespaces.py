"""한컴 호환 HWPML 파트 직렬화 계약.

정품 한컴 산출물은 header.xml·section0.xml 루트에 XML 선언(standalone="yes")과
네임스페이스 15종을 항상 선언한다. ET는 실제 사용된 프리픽스만 방출하므로
후처리 재직렬화 시 이 선언들이 소실된다(python-hwpx 6.0.2 편집기 안전성 게이트가
error 4종으로 검출).
"""

import re
import unittest
import xml.etree.ElementTree as ET

from table_hwpx_styles import serialize_hwpml_part

# python-hwpx 6.0.2 hwpx.oxml.namespaces.HWPML_COMPAT_ROOT_NAMESPACES 와 동일
EXPECTED_NAMESPACES = {
    "ha": "http://www.hancom.co.kr/hwpml/2011/app",
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hp10": "http://www.hancom.co.kr/hwpml/2016/paragraph",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
    "hhs": "http://www.hancom.co.kr/hwpml/2011/history",
    "hm": "http://www.hancom.co.kr/hwpml/2011/master-page",
    "hpf": "http://www.hancom.co.kr/schema/2011/hpf",
    "dc": "http://purl.org/dc/elements/1.1/",
    "opf": "http://www.idpf.org/2007/opf/",
    "ooxmlchart": "http://www.hancom.co.kr/hwpml/2016/ooxmlchart",
    "hwpunitchar": "http://www.hancom.co.kr/hwpml/2016/HwpUnitChar",
    "epub": "http://www.idpf.org/2007/ops",
    "config": "urn:oasis:names:tc:opendocument:xmlns:config:1.0",
}

HH = EXPECTED_NAMESPACES["hh"]
HC = EXPECTED_NAMESPACES["hc"]
HP = EXPECTED_NAMESPACES["hp"]
HS = EXPECTED_NAMESPACES["hs"]

HEADER_XML = (
    f'<hh:head xmlns:hh="{HH}" xmlns:hc="{HC}" version="1.4" secCnt="1">'
    '<hh:refList><hh:borderFills itemCnt="1">'
    '<hh:borderFill id="1"><hc:leftBorder type="SOLID" width="0.12 mm"/></hh:borderFill>'
    "</hh:borderFills></hh:refList></hh:head>"
)
SECTION_XML = (
    f'<hs:sec xmlns:hs="{HS}" xmlns:hp="{HP}">'
    '<hp:p><hp:run><hp:t>본문</hp:t></hp:run></hp:p>'
    "</hs:sec>"
)


def root_open_tag(payload: bytes) -> str:
    text = payload.decode("utf-8")
    start = text.index("<", text.index("?>") + 2)
    return text[start : text.index(">", start) + 1]


def declared_namespaces(payload: bytes) -> dict[str, str]:
    return dict(re.findall(r'xmlns:([\w.-]+)="([^"]*)"', root_open_tag(payload)))


class SerializeHwpmlPartTest(unittest.TestCase):
    def test_xml_declaration_is_standalone_yes(self):
        for label, source in (("header", HEADER_XML), ("section", SECTION_XML)):
            with self.subTest(part=label):
                payload = serialize_hwpml_part(ET.fromstring(source))
                self.assertTrue(
                    payload.startswith(
                        b'<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
                    ),
                    payload[:80],
                )

    def test_all_hancom_root_namespaces_declared(self):
        for label, source in (("header", HEADER_XML), ("section", SECTION_XML)):
            with self.subTest(part=label):
                declared = declared_namespaces(serialize_hwpml_part(ET.fromstring(source)))
                self.assertEqual(EXPECTED_NAMESPACES, declared)

    def test_no_duplicate_declarations(self):
        """중복 선언은 XML 파싱 자체를 깨뜨려 결함을 오히려 악화시킨다."""
        for label, source in (("header", HEADER_XML), ("section", SECTION_XML)):
            with self.subTest(part=label):
                open_tag = root_open_tag(serialize_hwpml_part(ET.fromstring(source)))
                prefixes = re.findall(r'xmlns:([\w.-]+)="', open_tag)
                self.assertEqual(sorted(set(prefixes)), sorted(prefixes))

    def test_document_body_is_unchanged(self):
        """선언부 외 본문 바이트는 ET 기본 직렬화와 동일해야 한다(서식 무변경 보장)."""
        for label, source in (("header", HEADER_XML), ("section", SECTION_XML)):
            with self.subTest(part=label):
                root = ET.fromstring(source)
                for prefix, uri in EXPECTED_NAMESPACES.items():
                    ET.register_namespace(prefix, uri)
                expected = ET.tostring(root, encoding="unicode")
                actual = serialize_hwpml_part(root).decode("utf-8")
                actual = actual[actual.index("?>") + 2 :].lstrip("\r\n")
                stripped = re.sub(r' xmlns:[\w.-]+="[^"]*"', "", actual)
                self.assertEqual(re.sub(r' xmlns:[\w.-]+="[^"]*"', "", expected), stripped)

    def test_self_closing_root_is_not_corrupted(self):
        payload = serialize_hwpml_part(ET.fromstring(f'<hs:sec xmlns:hs="{HS}"/>'))
        ET.fromstring(payload)  # 파싱 가능해야 함
        self.assertEqual(EXPECTED_NAMESPACES, declared_namespaces(payload))


if __name__ == "__main__":
    unittest.main()
