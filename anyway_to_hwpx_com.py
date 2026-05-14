"""
HWP COM 자동화로 Markdown / TXT / DOCX / HTML / CSV / XLSX / PDF → HWPX 변환.
확장자를 자동 감지하여 내부 blocks 구조로 정규화한 뒤 HWP COM으로 저장.
"""
from pathlib import Path
import argparse
import csv
import math
import os
import re
import subprocess
import sys
import time
import unicodedata

import win32com.client

SUPPORTED_EXTENSIONS = {'.md', '.txt', '.docx', '.html', '.htm', '.csv', '.xlsx', '.pdf'}
OPTIONAL_DEPENDENCIES = {
    '.docx': 'python-docx',
    '.html': 'beautifulsoup4',
    '.htm': 'beautifulsoup4',
    '.xlsx': 'openpyxl',
    '.pdf': 'kordoc, pdfplumber, PyMuPDF 또는 pypdf',
}


def as_path(value):
    return Path(value).expanduser().resolve()


def read_text_file(path):
    for encoding in ('utf-8-sig', 'utf-8', 'cp949'):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError('unknown', b'', 0, 1, f'텍스트 인코딩을 판별할 수 없음: {path}')


def require_file(path):
    if not path.exists():
        raise FileNotFoundError(f'입력 파일을 찾을 수 없음: {path}')
    if not path.is_file():
        raise ValueError(f'입력 경로가 파일이 아님: {path}')


# ─── Markdown 파서 ─────────────────────────────────────────────────────────────

def _clean_inline(text):
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'!\[[^\]]*\]\([^\)]+\)', '', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)
    text = text.replace('&nbsp;', ' ')
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


def _is_separator(line):
    if len(line) > 500:
        return False
    cells = line.strip().strip('|').split('|')
    return len(cells) >= 1 and all(re.match(r'^[ \t]*:?-+:?[ \t]*$', c) for c in cells)


def _parse_table_row(line):
    line = line.strip().strip('|')
    return [_clean_inline(c.strip()) for c in line.split('|')]


def _detect_list_item(line):
    stripped = line.strip()
    checks = [
        (7, re.compile(r'^([㉮㉯㉰㉱㉲㉳㉴㉵㉶㉷])\s+(.*)')),
        (6, re.compile(r'^([①②③④⑤⑥⑦⑧⑨⑩])\s+(.*)')),
        (5, re.compile(r'^(\([가나다라마바사아자차카타파하]\))\s+(.*)')),
        (4, re.compile(r'^(\(\d+\))\s+(.*)')),
        (3, re.compile(r'^([가나다라마바사아자차카타파하]\))\s+(.*)')),
        (2, re.compile(r'^(\d+\))\s+(.*)')),
        (1, re.compile(r'^([가나다라마바사아자차카타파하]\.)\s+(.*)')),
        (0, re.compile(r'^(\d+\.)\s+(.*)')),
    ]
    for depth, pattern in checks:
        m = pattern.match(stripped)
        if m:
            marker = m.group(1)
            content = _clean_inline(m.group(2))
            return (depth, f'{marker} {content}')
    m = re.match(r'^[-*]\s+(.*)', stripped)
    if m:
        return (0, '• ' + _clean_inline(m.group(1)))
    return None


def parse_markdown(text):
    lines = text.splitlines()
    blocks = []
    i = 0
    in_front = False

    while i < len(lines):
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        if line.strip() == '---':
            if i == 0:
                in_front = True
                i += 1
                continue
            elif in_front:
                in_front = False
                i += 1
                continue
            else:
                blocks.append({'type': 'hr'})
                i += 1
                continue

        if in_front:
            i += 1
            continue

        stripped_line = line.strip()

        if re.match(r'^(수신|경유|제목)\s*:', stripped_line):
            colon_idx = stripped_line.index(':')
            key = stripped_line[:colon_idx].strip()
            value = _clean_inline(stripped_line[colon_idx + 1:].strip())
            blocks.append({'type': 'official_header', 'key': key, 'value': value})
            i += 1
            continue

        if re.match(r'^-{3,}\s*$', line) or re.match(r'^\*{3,}\s*$', line):
            blocks.append({'type': 'hr'})
            i += 1
            continue

        m = re.match(r'^(#{1,3})\s+(.*)', line)
        if m:
            blocks.append({'type': 'h', 'level': len(m.group(1)), 'text': _clean_inline(m.group(2))})
            i += 1
            continue

        if line.strip().startswith('|') and i + 1 < len(lines) and _is_separator(lines[i + 1]):
            header = _parse_table_row(line)
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append(_parse_table_row(lines[i]))
                i += 1
            blocks.append({'type': 'table', 'header': header, 'rows': rows})
            continue

        li_result = _detect_list_item(line)
        if li_result:
            depth, text = li_result
            blocks.append({'type': 'li', 'text': text, 'depth': depth})
            i += 1
            continue

        if line.strip().startswith('>'):
            text = re.sub(r'^>\s*', '', line.strip())
            if text:
                blocks.append({'type': 'bq', 'text': _clean_inline(text)})
            i += 1
            continue

        if line.strip().startswith('```'):
            i += 1
            code_lines = []
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            i += 1
            for cl in code_lines:
                if cl.strip():
                    blocks.append({'type': 'code', 'text': cl})
            continue

        t = _clean_inline(line)
        if t:
            blocks.append({'type': 'p', 'text': t})
        i += 1

    return blocks


def parse_plain_text(text):
    blocks = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        li_result = _detect_list_item(line)
        if li_result:
            depth, item_text = li_result
            blocks.append({'type': 'li', 'text': item_text, 'depth': depth})
        else:
            blocks.append({'type': 'p', 'text': _clean_inline(line)})
    return blocks


def parse_html(text):
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise RuntimeError('HTML 변환에는 beautifulsoup4가 필요함: pip install beautifulsoup4') from exc

    soup = BeautifulSoup(text, 'html.parser')
    blocks = []
    body = soup.body or soup
    for node in body.find_all(['h1', 'h2', 'h3', 'p', 'blockquote', 'pre', 'table', 'li'], recursive=True):
        if node.find_parent(['table']) and node.name != 'table':
            continue
        if node.find_parent(['blockquote', 'pre']) and node.name not in ('blockquote', 'pre'):
            continue
        if node.find_parent('li') and node.name != 'li':
            continue
        if node.name in ('h1', 'h2', 'h3'):
            level = int(node.name[1])
            value = node.get_text(' ', strip=True)
            if value:
                blocks.append({'type': 'h', 'level': level, 'text': _clean_inline(value)})
        elif node.name == 'p':
            value = node.get_text(' ', strip=True)
            if value:
                blocks.append({'type': 'p', 'text': _clean_inline(value)})
        elif node.name == 'blockquote':
            value = node.get_text(' ', strip=True)
            if value:
                blocks.append({'type': 'bq', 'text': _clean_inline(value)})
        elif node.name == 'pre':
            value = node.get_text('\n', strip=True)
            for line in value.splitlines():
                if line.strip():
                    blocks.append({'type': 'code', 'text': line.rstrip()})
        elif node.name == 'li':
            parts = []
            for child in node.contents:
                if getattr(child, 'name', None) in ('ul', 'ol'):
                    continue
                if hasattr(child, 'get_text'):
                    child_text = child.get_text(' ', strip=True)
                else:
                    child_text = str(child).strip()
                if child_text:
                    parts.append(child_text)
            value = ' '.join(parts)
            if value:
                depth = len(node.find_parents(['ul', 'ol'])) - 1
                blocks.append({'type': 'li', 'text': _clean_inline(value), 'depth': max(depth, 0)})
        elif node.name == 'table':
            rows = []
            for tr in node.find_all('tr'):
                cells = [cell.get_text(' ', strip=True) for cell in tr.find_all(['th', 'td'])]
                if cells:
                    rows.append(cells)
            if rows:
                blocks.append({'type': 'table', 'header': rows[0], 'rows': rows[1:]})
    return blocks


def parse_csv_file(path):
    text = read_text_file(path)
    sample = text[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample)
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.reader(text.splitlines(), dialect))
    rows = [[_clean_inline(cell.strip()) for cell in row] for row in rows if any(cell.strip() for cell in row)]
    if not rows:
        return []
    return [{'type': 'table', 'header': rows[0], 'rows': rows[1:]}]


def parse_xlsx(path):
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise RuntimeError('XLSX 변환에는 openpyxl이 필요함: pip install openpyxl') from exc

    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        blocks = []
        for ws in wb.worksheets:
            rows = []
            for row in ws.iter_rows(values_only=True):
                values = ['' if value is None else _clean_inline(str(value)) for value in row]
                while values and values[-1] == '':
                    values.pop()
                if any(values):
                    rows.append(values)
            if not rows:
                continue
            blocks.append({'type': 'h', 'level': 2, 'text': ws.title})
            blocks.append({'type': 'table', 'header': rows[0], 'rows': rows[1:]})
        return blocks
    finally:
        wb.close()


def try_kordoc_pdf_text(path):
    kordoc_dir = Path(r'C:/Users/홍주형/kordoc-ai')
    if not kordoc_dir.exists():
        return None
    candidates = [
        ['python', str(kordoc_dir / 'main.py'), str(path)],
        ['python', '-m', 'kordoc', str(path)],
    ]
    for cmd in candidates:
        try:
            result = subprocess.run(
                cmd,
                cwd=str(kordoc_dir),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=120,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        output = (result.stdout or '').strip()
        if result.returncode == 0 and output:
            return output
    return None


def extract_pdf_text_fallback(path):
    errors = []

    try:
        import pdfplumber
        parts = []
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ''
                if text.strip():
                    parts.append(text)
        if parts:
            return '\n\n'.join(parts)
    except ImportError as exc:
        errors.append(f'pdfplumber 없음: {exc}')
    except Exception as exc:
        errors.append(f'pdfplumber 실패: {exc}')

    try:
        import fitz
        parts = []
        with fitz.open(str(path)) as doc:
            for page in doc:
                text = page.get_text('text') or ''
                if text.strip():
                    parts.append(text)
        if parts:
            return '\n\n'.join(parts)
    except ImportError as exc:
        errors.append(f'PyMuPDF 없음: {exc}')
    except Exception as exc:
        errors.append(f'PyMuPDF 실패: {exc}')

    try:
        from pypdf import PdfReader
    except ImportError as exc:
        errors.append(f'pypdf 없음: {exc}')
    else:
        try:
            reader = PdfReader(str(path))
            parts = []
            for page in reader.pages:
                text = page.extract_text() or ''
                if text.strip():
                    parts.append(text)
            if parts:
                return '\n\n'.join(parts)
        except Exception as exc:
            errors.append(f'pypdf 실패: {exc}')

    detail = '; '.join(errors) if errors else '사용 가능한 PDF 텍스트 추출기가 없음'
    raise RuntimeError(f'PDF 텍스트 추출 실패: {detail}')


def parse_pdf(path):
    text = try_kordoc_pdf_text(path)
    if text is None:
        text = extract_pdf_text_fallback(path)
    if not text.strip():
        raise RuntimeError(f'PDF에서 텍스트를 추출하지 못함: {path}')
    return parse_plain_text(text)


# ─── DOCX 파서 ─────────────────────────────────────────────────────────────────

def _iter_block_items(doc):
    from docx.oxml.ns import qn
    from docx.table import Table as DocxTable
    from docx.text.paragraph import Paragraph as DocxParagraph

    body = doc.element.body
    for child in body.iterchildren():
        if child.tag == qn('w:p'):
            yield DocxParagraph(child, doc)
        elif child.tag == qn('w:tbl'):
            yield DocxTable(child, doc)


def _para_text(para):
    from docx.oxml.ns import qn
    parts = []
    for run in para.runs:
        has_image = (
            run._r.find(qn('w:drawing')) is not None
            or run._r.find(qn('w:pict')) is not None
        )
        if not has_image:
            parts.append(run.text)
    return ''.join(parts).strip()


def _list_depth(para):
    from docx.oxml.ns import qn
    pPr = para._p.pPr
    if pPr is None:
        return -1
    numPr = pPr.find(qn('w:numPr'))
    if numPr is None:
        return -1
    ilvl = numPr.find(qn('w:ilvl'))
    if ilvl is None:
        return 0
    try:
        return int(ilvl.get(qn('w:val'), 0))
    except (TypeError, ValueError):
        return 0


def parse_docx(docx_path):
    try:
        from docx import Document
        from docx.table import Table as DocxTable
    except ImportError as exc:
        raise RuntimeError('DOCX 변환에는 python-docx가 필요함: pip install python-docx') from exc

    doc = Document(docx_path)
    blocks = []

    for item in _iter_block_items(doc):
        if isinstance(item, DocxTable):
            if not item.rows:
                continue
            header = [cell.text.strip() for cell in item.rows[0].cells]
            rows = [[cell.text.strip() for cell in row.cells] for row in item.rows[1:]]
            if all(not h for h in header) and not rows:
                continue
            blocks.append({'type': 'table', 'header': header, 'rows': rows})
            continue

        para = item
        style_name = para.style.name if para.style else ''
        text = _para_text(para)

        if not text:
            continue

        heading_match = re.match(r'^(?:Heading|제목|머리말)\s*(\d+)$', style_name, re.IGNORECASE)
        if heading_match:
            level = max(1, min(int(heading_match.group(1)), 3))
            blocks.append({'type': 'h', 'level': level, 'text': text})
            continue

        depth = _list_depth(para)
        if depth >= 0:
            blocks.append({'type': 'li', 'text': text, 'depth': min(depth, 7)})
            continue

        if re.search(r'[Qq]uote|인용', style_name):
            blocks.append({'type': 'bq', 'text': text})
            continue

        if re.search(r'[Cc]ode|코드', style_name):
            blocks.append({'type': 'code', 'text': text})
            continue

        if re.match(r'^(수신|경유|제목)\s*:', text):
            colon_idx = text.index(':')
            key = text[:colon_idx].strip()
            value = text[colon_idx + 1:].strip()
            blocks.append({'type': 'official_header', 'key': key, 'value': value})
            continue

        if re.search(r'[Hh]orizontal|구분선', style_name):
            blocks.append({'type': 'hr'})
            continue

        blocks.append({'type': 'p', 'text': text})

    return blocks


# ─── 확장자 자동 감지 ──────────────────────────────────────────────────────────

def detect_and_parse(file_path):
    path = as_path(file_path)
    require_file(path)
    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        supported = ', '.join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f'지원하지 않는 형식: {ext}  (지원: {supported})')
    if ext == '.md':
        return parse_markdown(read_text_file(path))
    if ext == '.txt':
        return parse_plain_text(read_text_file(path))
    if ext == '.docx':
        return parse_docx(str(path))
    if ext in ('.html', '.htm'):
        return parse_html(read_text_file(path))
    if ext == '.csv':
        return parse_csv_file(path)
    if ext == '.xlsx':
        return parse_xlsx(path)
    if ext == '.pdf':
        return parse_pdf(path)
    raise ValueError(f'지원하지 않는 형식: {ext}')


# ─── HWP COM 헬퍼 ─────────────────────────────────────────────────────────────

def insert_text(hwp, text):
    hwp.HAction.GetDefault('InsertText', hwp.HParameterSet.HInsertText.HSet)
    hwp.HParameterSet.HInsertText.Text = text
    hwp.HAction.Execute('InsertText', hwp.HParameterSet.HInsertText.HSet)


def break_para(hwp):
    hwp.HAction.Run('BreakPara')


def set_char_shape(hwp, height=1300, bold=False, italic=False, font='body'):
    face_hangul = '휴먼명조' if font == 'body' else '맑은 고딕'
    face_latin = 'Arial'
    act = hwp.CreateAction('CharShape')
    pset = act.CreateSet()
    act.GetDefault(pset)
    pset.SetItem('Height', height)
    pset.SetItem('Bold', bold)
    pset.SetItem('Italic', italic)
    pset.SetItem('FaceNameHangul', face_hangul)
    pset.SetItem('FaceNameLatin', face_latin)
    act.Execute(pset)


def set_para_shape(hwp, align=0, space_before=0, space_after=0, indent_left=0, indent_first=0):
    act = hwp.CreateAction('ParagraphShape')
    pset = act.CreateSet()
    act.GetDefault(pset)
    pset.SetItem('Align', align)
    pset.SetItem('SpaceBefore', space_before)
    pset.SetItem('SpaceAfter', space_after)
    pset.SetItem('IndentLeft', indent_left)
    pset.SetItem('IndentFirst', indent_first)
    act.Execute(pset)


# ─── 표 레이아웃 산정 ─────────────────────────────────────────────────────────

TABLE_TOTAL_WIDTH = 14000
TABLE_MIN_ROW_HEIGHT = 900
TABLE_LINE_HEIGHT = 620
TABLE_CELL_VPAD = 260
TABLE_CELL_HPAD = 240
TABLE_UNIT_PER_VISUAL = 135

COLUMN_PROFILES = {
    'index': {'min': 650, 'pref': 850, 'max': 1100, 'weight': 0.3},
    'number': {'min': 900, 'pref': 1300, 'max': 1900, 'weight': 0.6},
    'date': {'min': 1200, 'pref': 1700, 'max': 2300, 'weight': 0.7},
    'name': {'min': 850, 'pref': 1200, 'max': 1700, 'weight': 0.5},
    'position': {'min': 1000, 'pref': 1500, 'max': 2200, 'weight': 0.6},
    'org': {'min': 1600, 'pref': 2500, 'max': 3600, 'weight': 1.0},
    'title': {'min': 1700, 'pref': 2800, 'max': 4200, 'weight': 1.2},
    'detail': {'min': 2200, 'pref': 4300, 'max': 8200, 'weight': 2.3},
    'generic': {'min': 1200, 'pref': 1900, 'max': 3200, 'weight': 1.0},
}

DETAIL_HEADER_PATTERN = re.compile(
    r'(내용|세부|비고|사유|설명|의견|주소|목적|방법|추진|계획|결과|특이|주요|개요|'
    r'remark|note|description|detail|comment)',
    re.IGNORECASE,
)
ORG_HEADER_PATTERN = re.compile(r'(기관|학교|부서|소속|단체|업체|교육청|지원청|org|organization|department)', re.IGNORECASE)
TITLE_HEADER_PATTERN = re.compile(r'(명칭|제목|사업명|프로그램명|과정명|행사명|title|subject)', re.IGNORECASE)
VALUE_HEADER_PATTERN = re.compile(r'^(값|내용|value)$', re.IGNORECASE)
POSITION_HEADER_PATTERN = re.compile(r'(직위|직급|직책|보직|담당|role|position|rank)', re.IGNORECASE)
NAME_HEADER_PATTERN = re.compile(r'(성명|이름|성함|신청자|담당자|name)', re.IGNORECASE)
DATE_HEADER_PATTERN = re.compile(r'(일자|날짜|기간|시간|시각|연도|월일|date|time|period)', re.IGNORECASE)
NUMBER_HEADER_PATTERN = re.compile(r'(금액|예산|단가|합계|수량|인원|계|원|명|건|회|비율|%|amount|price|total|count|number)', re.IGNORECASE)
INDEX_HEADER_PATTERN = re.compile(r'^(순번|연번|번호|no\.?|#)$', re.IGNORECASE)
NUMBER_VALUE_PATTERN = re.compile(r'^\s*[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\s*(?:원|명|건|회|%|개|점)?\s*$')
DATE_VALUE_PATTERN = re.compile(r'^\s*\d{2,4}[./-]\d{1,2}(?:[./-]\d{1,2})?(?:\s*[-~]\s*\d{1,2}[./-]\d{1,2})?\s*$')

def _visual_width(text):
    w = 0
    for ch in str(text or ''):
        if unicodedata.combining(ch):
            continue
        if unicodedata.east_asian_width(ch) in ('F', 'W'):
            w += 2
        else:
            w += 1
    return max(w, 1)


def _normalize_table_rows(header, rows):
    all_rows = ([header] if header else []) + (rows if rows else [])
    n = max((len(row) for row in all_rows), default=0)
    normalized = []
    for row in all_rows:
        values = [str(cell or '').strip() for cell in row]
        normalized.append(values + [''] * (n - len(values)))
    return normalized, n


def _percentile(values, ratio):
    if not values:
        return 1
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, math.ceil(len(ordered) * ratio) - 1))
    return ordered[idx]


def _infer_col_kind(header_text, values, col_index):
    header_text = str(header_text or '').strip()
    body_values = [str(v or '').strip() for v in values if str(v or '').strip()]
    if INDEX_HEADER_PATTERN.search(header_text):
        return 'index'
    if VALUE_HEADER_PATTERN.search(header_text):
        return 'detail'
    if DETAIL_HEADER_PATTERN.search(header_text):
        return 'detail'
    if ORG_HEADER_PATTERN.search(header_text):
        return 'org'
    if TITLE_HEADER_PATTERN.search(header_text):
        return 'title'
    if POSITION_HEADER_PATTERN.search(header_text):
        return 'position'
    if NAME_HEADER_PATTERN.search(header_text):
        return 'name'
    if DATE_HEADER_PATTERN.search(header_text):
        return 'date'
    if NUMBER_HEADER_PATTERN.search(header_text):
        return 'number'
    if col_index == 0 and body_values and all(_visual_width(v) <= 4 for v in body_values):
        return 'index'
    if body_values:
        numeric_hits = sum(1 for v in body_values if NUMBER_VALUE_PATTERN.match(v))
        date_hits = sum(1 for v in body_values if DATE_VALUE_PATTERN.match(v))
        if numeric_hits / len(body_values) >= 0.75:
            return 'number'
        if date_hits / len(body_values) >= 0.6:
            return 'date'
        widths = [_visual_width(v) for v in body_values]
        avg_width = sum(widths) / len(widths)
        p90_width = _percentile(widths, 0.9)
        if p90_width >= 28 or avg_width >= 18:
            return 'detail'
        if avg_width <= 8 and all(' ' not in v for v in body_values[:10]):
            return 'name'
    return 'generic'


def _content_preferred_width(kind, header_text, values):
    widths = [_visual_width(header_text)]
    widths.extend(_visual_width(v) for v in values if str(v or '').strip())
    p90 = _percentile(widths, 0.9)
    longest = max(widths or [1])
    if kind == 'detail':
        visual_units = min(max(p90, 18), 42)
    elif kind in ('org', 'title'):
        visual_units = min(max(p90, 12), 28)
    elif kind in ('number', 'date', 'position'):
        visual_units = min(max(longest, 7), 18)
    elif kind == 'index':
        visual_units = min(max(longest, 3), 6)
    else:
        visual_units = min(max(p90, 8), 22)
    return int(visual_units * TABLE_UNIT_PER_VISUAL + TABLE_CELL_HPAD)


def _redistribute_widths(widths, kinds, total):
    if not widths:
        return []
    profiles = [COLUMN_PROFILES[k] for k in kinds]
    min_sum = sum(p['min'] for p in profiles)
    if min_sum >= total:
        result = [max(1, int(total * p['min'] / min_sum)) for p in profiles]
    else:
        result = widths[:]

    overflow = sum(result) - total
    if overflow > 0:
        shrink_room = [max(0, result[i] - profiles[i]['min']) for i in range(len(result))]
        room_sum = sum(shrink_room)
        if room_sum > 0:
            for i, room in enumerate(shrink_room):
                cut = min(room, int(overflow * room / room_sum))
                result[i] -= cut
            overflow = sum(result) - total
        while overflow > 0:
            i = max(range(len(result)), key=lambda idx: result[idx] - profiles[idx]['min'])
            if result[i] <= profiles[i]['min']:
                break
            result[i] -= 1
            overflow -= 1
    else:
        extra = total - sum(result)
        weights = [
            profiles[i]['weight'] * max(0.25, profiles[i]['max'] - result[i])
            for i in range(len(result))
        ]
        weight_sum = sum(weights)
        if weight_sum > 0:
            for i, weight in enumerate(weights):
                add = min(profiles[i]['max'] - result[i], int(extra * weight / weight_sum))
                result[i] += max(add, 0)
            extra = total - sum(result)
        while extra > 0:
            growable = [i for i, p in enumerate(profiles) if result[i] < p['max']]
            if not growable:
                break
            i = max(growable, key=lambda idx: profiles[idx]['weight'])
            result[i] += 1
            extra -= 1
        if extra > 0:
            soft_weights = [p['weight'] for p in profiles]
            soft_sum = sum(soft_weights) or len(result)
            for i, weight in enumerate(soft_weights):
                add = int(extra * weight / soft_sum)
                result[i] += add
            extra = total - sum(result)
            for i in range(extra):
                result[i % len(result)] += 1

    diff = total - sum(result)
    if diff:
        target = max(range(len(result)), key=lambda idx: profiles[idx]['weight'])
        result[target] += diff
    return result


def calc_col_widths(header, rows, total=14000):
    normalized, n = _normalize_table_rows(header or [], rows or [])
    if n == 0:
        return []
    if n == 1:
        return [total]
    kinds = []
    preferred = []
    for ci in range(n):
        header_text = normalized[0][ci] if header else ''
        values = [row[ci] for row in normalized[1 if header else 0:]]
        kind = _infer_col_kind(header_text, values, ci)
        profile = COLUMN_PROFILES[kind]
        content_width = _content_preferred_width(kind, header_text, values)
        kinds.append(kind)
        preferred.append(max(profile['min'], min(profile['max'], max(profile['pref'], content_width))))
    return _redistribute_widths(preferred, kinds, total)


def calc_row_heights(header, rows, col_widths):
    normalized, n = _normalize_table_rows(header or [], rows or [])
    if not normalized or not col_widths:
        return []
    heights = []
    for row in normalized:
        max_lines = 1
        for ci in range(n):
            text = row[ci]
            if not text:
                continue
            usable_width = max(300, col_widths[min(ci, len(col_widths) - 1)] - TABLE_CELL_HPAD)
            capacity = max(2, int(usable_width / TABLE_UNIT_PER_VISUAL))
            visual_lines = 0
            for part in str(text).splitlines() or ['']:
                visual_lines += max(1, math.ceil(_visual_width(part) / capacity))
            max_lines = max(max_lines, visual_lines)
        heights.append(max(TABLE_MIN_ROW_HEIGHT, TABLE_CELL_VPAD + max_lines * TABLE_LINE_HEIGHT))
    return heights


def insert_table(hwp, header, rows):
    all_rows = ([header] if header else []) + rows
    if not all_rows:
        return
    num_rows = len(all_rows)
    num_cols = max(len(r) for r in all_rows)
    col_widths = calc_col_widths(header or [], rows)
    row_heights = calc_row_heights(header or [], rows, col_widths)
    act = hwp.CreateAction('TableCreate')
    pset = act.CreateSet()
    act.GetDefault(pset)
    pset.SetItem('Rows', num_rows)
    pset.SetItem('Cols', num_cols)
    pset.SetItem('WidthType', 0)
    pset.SetItem('HeightType', 0)
    pset.SetItem('AutoHeight', True)
    for key, value in (('WidthValue', sum(col_widths)), ('HeightValue', sum(row_heights))):
        try:
            pset.SetItem(key, value)
        except Exception:
            pass
    act.Execute(pset)
    width_adjust_failed = False
    moved_right = 0
    try:
        for ci, w in enumerate(col_widths):
            sel_act = hwp.CreateAction('TableColWidth')
            if sel_act is None:
                raise RuntimeError('TableColWidth action unavailable')
            sel_pset = sel_act.CreateSet()
            sel_act.GetDefault(sel_pset)
            sel_pset.SetItem('Width', w)
            sel_act.Execute(sel_pset)
            if ci < num_cols - 1:
                hwp.HAction.Run('TableRightCell')
                moved_right += 1
    except Exception as e:
        width_adjust_failed = True
        print(f'[경고] 열 너비 조정 실패: {e}')
    finally:
        for _ in range(moved_right):
            hwp.HAction.Run('TableLeftCell')
    first_cell = True
    for ri, row in enumerate(all_rows):
        is_header = (ri == 0 and header is not None)
        for ci in range(num_cols):
            if not first_cell:
                hwp.HAction.Run('TableRightCell')
            first_cell = False
            cell_text = row[ci] if ci < len(row) else ''
            if is_header:
                set_para_shape(hwp, align=3)
                set_char_shape(hwp, height=1200, bold=True, font='table')
            else:
                set_para_shape(hwp, align=1)
                set_char_shape(hwp, height=1200, font='table')
            if cell_text:
                insert_text(hwp, cell_text)
    hwp.HAction.Run('MoveDocEnd')
    break_para(hwp)


# ─── 문서 빌드 ─────────────────────────────────────────────────────────────────

def build_doc(hwp, blocks):
    for blk in blocks:
        t = blk.get('type')

        if t == 'h':
            lv = blk['level']
            heights = {1: 1600, 2: 1400, 3: 1300}
            sbefore = {1: 500, 2: 400, 3: 300}
            safter = {1: 250, 2: 200, 3: 150}
            set_para_shape(hwp, align=1, space_before=sbefore.get(lv, 300), space_after=safter.get(lv, 150))
            set_char_shape(hwp, height=heights.get(lv, 1300), bold=True, font='body')
            insert_text(hwp, blk['text'])
            break_para(hwp)
            set_para_shape(hwp, align=0)
            set_char_shape(hwp, height=1300, font='body')

        elif t == 'p':
            set_para_shape(hwp, align=0)
            set_char_shape(hwp, height=1300, font='body')
            insert_text(hwp, blk['text'])
            break_para(hwp)

        elif t == 'li':
            depth = blk.get('depth', 0)
            set_para_shape(hwp, align=1, indent_left=depth * 400, indent_first=0)
            set_char_shape(hwp, height=1300, font='body')
            insert_text(hwp, blk['text'])
            break_para(hwp)

        elif t == 'bq':
            set_para_shape(hwp, align=1, indent_left=600)
            set_char_shape(hwp, height=1200, italic=True, font='body')
            insert_text(hwp, blk['text'])
            break_para(hwp)

        elif t == 'code':
            set_para_shape(hwp, align=1, indent_left=600)
            set_char_shape(hwp, height=1100, font='table')
            insert_text(hwp, blk['text'])
            break_para(hwp)

        elif t == 'hr':
            set_para_shape(hwp, align=3)
            set_char_shape(hwp, height=1000, font='body')
            insert_text(hwp, '─' * 30)
            break_para(hwp)

        elif t == 'table':
            set_para_shape(hwp, align=0)
            set_char_shape(hwp, height=1200, font='table')
            insert_table(hwp, blk.get('header'), blk.get('rows', []))

        elif t == 'official_header':
            set_para_shape(hwp, align=1)
            set_char_shape(hwp, height=1200, font='table')
            label = blk['key'].ljust(4)
            insert_text(hwp, label + '  ' + blk['value'])
            break_para(hwp)


def _insert_end_mark(hwp, blocks):
    if not blocks:
        return
    last = blocks[-1]
    last_text = last.get('text', '') or ''
    if last_text.strip().endswith('끝'):
        return
    if last['type'] == 'table':
        last_rows = last.get('rows', [])
        if last_rows:
            last_row_text = ' '.join(last_rows[-1])
            if last_row_text.strip().endswith('끝') or last_row_text.strip() == '이하 빈칸':
                return
        hwp.HAction.Run('MoveDocEnd')
        set_para_shape(hwp, align=1)
        set_char_shape(hwp, height=1300, font='body')
        insert_text(hwp, ' 끝')
        break_para(hwp)
    else:
        hwp.HAction.Run('MoveDocEnd')
        set_para_shape(hwp, align=1)
        set_char_shape(hwp, height=1300, font='body')
        insert_text(hwp, '  끝')
        break_para(hwp)


# ─── 변환 실행 ─────────────────────────────────────────────────────────────────

def build_output_path(src_path, output_dir):
    src = as_path(src_path)
    out_dir = as_path(output_dir) if output_dir else src.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    candidate = out_dir / f'{src.stem}.hwpx'
    if not candidate.exists():
        return candidate
    for idx in range(2, 1000):
        candidate = out_dir / f'{src.stem} - {idx}.hwpx'
        if not candidate.exists():
            return candidate
    raise FileExistsError(f'저장 가능한 파일명을 찾지 못함: {out_dir / (src.stem + ".hwpx")}')


def convert_file(hwp, src_path, hwpx_path, insert_end_mark=False):
    src = as_path(src_path)
    out = as_path(hwpx_path)
    blocks = detect_and_parse(src)

    hwp.XHwpDocuments.Add(isTab=False)
    time.sleep(0.5)
    doc = hwp.XHwpDocuments.Item(hwp.XHwpDocuments.Count - 1)

    try:
        build_doc(hwp, blocks)
        if insert_end_mark:
            _insert_end_mark(hwp, blocks)
        hwp.SaveAs(str(out), 'HWPX', '')
        time.sleep(0.5)
    finally:
        doc.Close(isDirty=False)
        time.sleep(0.3)
    ext = src.suffix.upper().lstrip('.')
    print(f'[완료] {ext} → {out.name}')


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Markdown / TXT / DOCX / HTML / CSV / XLSX / PDF → HWPX 변환 (HWP COM 방식)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('files', nargs='*', help='변환할 파일 경로')
    parser.add_argument('-o', '--output-dir', default=None, help='저장할 폴더 경로 (기본: 입력 파일과 같은 폴더)')
    parser.add_argument('--insert-end-mark', action='store_true', help="문서 끝에 '끝' 표시를 자동 삽입")
    parser.add_argument('--list-formats', action='store_true', help='지원 형식 목록 출력')
    args = parser.parse_args(argv)

    if args.list_formats:
        print('지원 입력 형식: ' + ', '.join(sorted(SUPPORTED_EXTENSIONS)))
        return 0

    if not args.files:
        parser.error('변환할 파일 경로가 필요함')

    hwp = None
    failures = []
    try:
        print('HWP 실행 중...')
        hwp = win32com.client.Dispatch('HWPFrame.HwpObject')
        hwp.RegisterModule('FilePathCheckDLL', 'SecurityModule')
        hwp.XHwpWindows.Item(0).Visible = True
        time.sleep(1.5)

        for src_arg in args.files:
            try:
                src_path = as_path(src_arg)
                hwpx_path = build_output_path(src_path, args.output_dir)
                print(f'변환 중: {src_path.name} → {hwpx_path.name}')
                convert_file(hwp, src_path, hwpx_path, insert_end_mark=args.insert_end_mark)
            except Exception as exc:
                failures.append((src_arg, exc))
                print(f'[실패] {src_arg}: {exc}', file=sys.stderr)
    finally:
        if hwp is not None:
            hwp.Quit()

    if failures:
        print('\n실패 목록:', file=sys.stderr)
        for src_arg, exc in failures:
            print(f'- {src_arg}: {exc}', file=sys.stderr)
        return 1
    print('\n전체 변환 완료.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
