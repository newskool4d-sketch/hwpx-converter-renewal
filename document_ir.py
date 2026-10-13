"""Map kordoc's structured document to the established COM block model.

The original parse result remains the inspection IR.  This adapter does not
claim to preserve source layout: it retains reading order and the rectangular
cell grid, then lets the existing institution layout engine build a new copy.
"""
from __future__ import annotations

from collections.abc import Mapping

KORDOC_INPUT_EXTENSIONS = frozenset({
    '.hwp', '.hwpx', '.hwpml', '.hml', '.docx', '.xlsx', '.xls', '.pptx', '.pdf',
})
MAX_TABLE_CELLS = 100_000
MAX_BLOCKS = 100_000


def kordoc_to_blocks(document: Mapping) -> tuple[list[dict], list[str]]:
    """Return converter blocks plus explicit loss warnings, without mutation."""
    if not isinstance(document, Mapping) or not isinstance(document.get('blocks'), list):
        raise ValueError('kordoc 문서에 blocks 배열이 없습니다.')
    result: list[dict] = []
    warnings: list[str] = []
    visited = 0

    def warn(message):
        if message not in warnings:
            warnings.append(message)

    def check_style(block):
        if block.get('style') or block.get('spans') or block.get('indent'):
            warn('원본 글꼴·강조·들여쓰기는 기관 기본 서식으로 변환합니다.')
        if block.get('href'):
            warn('하이퍼링크는 표시 텍스트만 유지하며 클릭 가능한 URL은 변환하지 않습니다.')
        if block.get('bbox'):
            warn('원본 페이지 좌표는 새 문서에서 재현하지 않습니다.')

    def table_block(block):
        table = block.get('table')
        if not isinstance(table, Mapping) or not isinstance(table.get('cells'), list):
            raise ValueError('kordoc 표에 cells 배열이 없습니다.')
        rows, cols = table.get('rows'), table.get('cols')
        if type(rows) is not int or type(cols) is not int or rows < 0 or cols < 0:
            raise ValueError('kordoc 표의 행·열 수가 올바르지 않습니다.')
        if rows * cols > MAX_TABLE_CELLS or rows > MAX_TABLE_CELLS or cols > MAX_TABLE_CELLS:
            raise ValueError('kordoc 표가 안전한 셀 처리 한도를 초과했습니다.')
        cells = table['cells']
        if len(cells) != rows or any(not isinstance(row, list) or len(row) != cols for row in cells):
            raise ValueError('kordoc 표의 행·열 수와 실제 셀 배열이 다릅니다.')
        if not rows or not cols:
            return None
        grid = [[''] * cols for _ in range(rows)]
        covered = set()
        merges = []
        for row_index, row in enumerate(cells):
            for col_index, cell in enumerate(row):
                if not isinstance(cell, Mapping):
                    raise ValueError('kordoc 표 셀의 구조가 올바르지 않습니다.')
                if (row_index, col_index) in covered:
                    # kordoc IR is a rectangular grid, including covered slots.
                    if cell.get('text'):
                        raise ValueError('병합으로 가려진 셀에 별도 본문이 있어 안전하게 변환할 수 없습니다.')
                    continue
                row_span, col_span = cell.get('rowSpan', 1), cell.get('colSpan', 1)
                if any(type(span) is not int or span < 1 for span in (row_span, col_span)):
                    raise ValueError('kordoc 표 셀의 병합 크기가 올바르지 않습니다.')
                if row_index + row_span > rows or col_index + col_span > cols:
                    raise ValueError('kordoc 표 셀 병합이 표 경계를 벗어났습니다.')
                grid[row_index][col_index] = str(cell.get('text') or '')
                for rr in range(row_index, row_index + row_span):
                    for cc in range(col_index, col_index + col_span):
                        if (rr, cc) == (row_index, col_index):
                            continue
                        if (rr, cc) in covered:
                            raise ValueError('kordoc 표 셀의 병합 영역이 겹칩니다.')
                        covered.add((rr, cc))
                if row_span > 1 or col_span > 1:
                    merges.append([row_index, col_index, row_span, col_span])
                for nested in cell.get('blocks') or []:
                    check_style(nested)
                    if nested.get('type') in ('table', 'image'):
                        warn('표 셀 내부 중첩표·이미지는 셀의 추출 텍스트만 유지합니다. 원본과 대조하세요.')
        has_header = table.get('hasHeader', False)
        converted = {
            'type': 'table', 'header': grid[0] if has_header else None,
            'rows': grid[1:] if has_header else grid, 'table_source': 'kordoc',
        }
        if merges:
            converted['merged_cells'] = merges
        if table.get('caption'):
            result.append({'type': 'p', 'text': str(table['caption'])})
            warn('표 캡션은 표 앞의 본문으로 배치합니다.')
        if table.get('captionBlocks'):
            warn('표 캡션 내부 구조는 캡션의 추출 텍스트만 유지합니다.')
        return converted

    def walk(blocks, depth=0):
        nonlocal visited
        if depth > 32:
            raise ValueError('kordoc 문서의 중첩 깊이가 처리 한도를 초과했습니다.')
        for block in blocks:
            visited += 1
            if visited > MAX_BLOCKS:
                raise ValueError('kordoc 문서의 블록 수가 처리 한도를 초과했습니다.')
            if not isinstance(block, Mapping):
                raise ValueError('kordoc 문서 블록의 구조가 올바르지 않습니다.')
            check_style(block)
            kind, text = block.get('type'), str(block.get('text') or '')
            if kind == 'table':
                converted = table_block(block)
                if converted:
                    result.append(converted)
            elif kind == 'heading':
                level = block.get('level', 1)
                level = max(1, min(level, 3)) if type(level) is int else 1
                result.append({'type': 'h', 'level': level, 'text': text})
            elif kind == 'paragraph':
                result.append({'type': 'bq' if block.get('quote') else 'p', 'text': text})
            elif kind == 'list':
                list_depth = block.get('listDepth', depth)
                list_depth = max(0, min(list_depth, 7)) if type(list_depth) is int else min(depth, 7)
                if text:
                    result.append({'type': 'li', 'text': text, 'depth': list_depth})
                walk(block.get('children') or [], depth + 1)
            elif kind == 'separator':
                result.append({'type': 'hr'})
            elif kind == 'image':
                warn('kordoc 이미지 메타데이터는 읽었으나 이미지 원본은 이 변환 경로에서 삽입하지 않습니다.')
            else:
                warn(f'지원하지 않는 kordoc 블록 유형: {kind!r}. 추출 텍스트만 유지합니다.')
                if text:
                    result.append({'type': 'p', 'text': text})
            if block.get('footnoteText'):
                result.append({'type': 'p', 'text': str(block['footnoteText'])})
                warn('각주·미주는 해당 블록 다음 본문으로 배치합니다.')

    walk(document['blocks'])
    return result, warnings
