"""Compare local pdfplumber and kordoc extraction without changing defaults.

Agreement is not accuracy. Supply a reviewed plain-text reference to measure
token recall. Reports contain metrics, not document text. Both paths keep OCR
disabled; this is a text-PDF comparison, not an OCR benchmark.
"""
from __future__ import annotations

import argparse
from collections import Counter
import contextlib
import io
import json
from pathlib import Path
import re
import sys
import time

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def tokens(text):
    return re.findall(r'[가-힣A-Za-z]+|\d+(?:[,.]\d+)*', text)


def block_text(blocks):
    parts = []
    for block in blocks:
        if block.get('type') == 'table':
            rows = ([block['header']] if block.get('header') else []) + block.get('rows', [])
            parts.extend(str(cell) for row in rows for cell in row)
        else:
            parts.append(str(block.get('text') or ''))
    return '\n'.join(parts)


def measure(name, action, expected):
    start = time.perf_counter()
    try:
        text, warnings = action()
        words = tokens(text)
        metrics = {'name': name, 'status': 'success', 'seconds': round(time.perf_counter() - start, 3),
                   'characters': len(text), 'tokens': len(words), 'warnings': warnings}
        if expected is not None:
            counts, target = Counter(words), Counter(tokens(expected))
            overlap = sum((counts & target).values())
            metrics['reference_token_recall'] = overlap / sum(target.values()) if target else None
            metrics['reference_token_precision'] = overlap / sum(counts.values()) if counts else None
        return metrics, words
    except Exception as exc:
        return {'name': name, 'status': 'error', 'seconds': round(time.perf_counter() - start, 3),
                'error_type': type(exc).__name__}, None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--reference', type=Path, help='Reviewed ground-truth plain text, UTF-8')
    parser.add_argument('--report', type=Path, required=True, help='New JSON report; existing files are refused')
    args = parser.parse_args(argv)
    if args.source.suffix.lower() != '.pdf' or not args.source.is_file():
        parser.error('source must be an existing PDF')
    if args.report.resolve() in {args.source.resolve(), args.reference.resolve() if args.reference else None}:
        parser.error('report must differ from input files')
    expected = args.reference.read_text(encoding='utf-8-sig') if args.reference else None
    if expected is not None and not tokens(expected):
        parser.error('reference must contain text tokens')
    # Reserve report before potentially expensive parsing, never overwrite.
    with args.report.open('x', encoding='utf-8') as output:
        from kordoc_client import KordocClient

        def legacy():
            import anyway_to_hwpx_com as converter
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                blocks = converter.extract_pdf_blocks_pdfplumber(args.source)
            if not blocks:
                raise ValueError('No text blocks')
            return block_text(blocks), []

        def kordoc():
            result = KordocClient().request('parse', path=args.source)
            if not result['ok']:
                raise RuntimeError('Document engine did not return a complete parse')
            # Report only codes, never the warning's possible document excerpt.
            warnings = [w.get('code', 'WARNING') if isinstance(w, dict) else 'WARNING'
                        for w in result.get('warnings', [])]
            return result['data'].get('markdown', ''), warnings

        a, a_tokens = measure('pdfplumber-local', legacy, expected)
        b, b_tokens = measure('kordoc-local-no-ocr', kordoc, expected)
        agreement = None
        if a_tokens is not None and b_tokens is not None:
            shared = sum((Counter(a_tokens) & Counter(b_tokens)).values())
            denominator = len(a_tokens) + len(b_tokens)
            agreement = 2 * shared / denominator if denominator else None
        report = {'engines': [a, b], 'token_multiset_agreement_f1': agreement,
                  'reference_supplied': expected is not None,
                  'note': 'Single-run observations; engine agreement is not extraction accuracy. '
                          'Reading order, table topology and rendering need separate review. '
                          'The default converter engine was not changed.'}
        json.dump(report, output, ensure_ascii=False, indent=2)
        output.write('\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if a['status'] == b['status'] == 'success' else 1


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
