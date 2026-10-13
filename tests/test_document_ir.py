from __future__ import annotations

import contextlib
import copy
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import anyway_to_hwpx_com as converter
from document_ir import KORDOC_INPUT_EXTENSIONS, kordoc_to_blocks


def cell(text='', row_span=1, col_span=1, **extra):
    return {'text': text, 'rowSpan': row_span, 'colSpan': col_span, **extra}


class DocumentIRTests(unittest.TestCase):
    def test_rectangular_grid_keeps_merge_coordinates_empty_rows_and_order(self):
        document = {'blocks': [
            {'type': 'paragraph', 'text': '전'},
            {'type': 'table', 'table': {'rows': 3, 'cols': 3, 'hasHeader': True, 'cells': [
                [cell('제목', 2, 2), cell(), cell('합계')],
                [cell(), cell(), cell('120,000원')],
                [cell(), cell(), cell()],
            ]}},
            {'type': 'paragraph', 'text': '후'},
        ]}
        before = copy.deepcopy(document)
        blocks, warnings = kordoc_to_blocks(document)
        self.assertEqual([block['type'] for block in blocks], ['p', 'table', 'p'])
        self.assertEqual(blocks[1]['header'], ['제목', '', '합계'])
        self.assertEqual(blocks[1]['rows'], [['', '', '120,000원'], ['', '', '']])
        self.assertEqual(blocks[1]['merged_cells'], [[0, 0, 2, 2]])
        self.assertEqual(document, before)
        self.assertEqual(warnings, [])

    def test_headerless_table_retains_all_rows_as_body(self):
        blocks, _ = kordoc_to_blocks({'blocks': [{'type': 'table', 'table': {
            'rows': 1, 'cols': 2, 'hasHeader': False, 'cells': [[cell('첫째'), cell('둘째')]],
        }}]})
        self.assertIsNone(blocks[0]['header'])
        self.assertEqual(blocks[0]['rows'], [['첫째', '둘째']])

    def test_table_corruption_rejected_instead_of_losing_cell_data(self):
        for table in [
            {'rows': 1, 'cols': 1, 'cells': [[cell('값', 1, 2)]]},
            {'rows': 1, 'cols': 2, 'cells': [[cell('병합', 1, 2), cell('손실 위험')]]},
            {'rows': 2, 'cols': 1, 'cells': [[cell('누락 행')]]},
            {'rows': 1, 'cols': 1, 'cells': [[cell('값', 0, 1)]]},
            {'rows': 1000000, 'cols': 1000000, 'cells': []},
        ]:
            with self.subTest(table=table), self.assertRaises(ValueError):
                kordoc_to_blocks({'blocks': [{'type': 'table', 'table': table}]})

    def test_nested_content_media_and_styles_have_explicit_warnings(self):
        document = {'blocks': [
            {'type': 'paragraph', 'text': '본문', 'style': {'bold': True}, 'href': 'https://example.test', 'footnoteText': '각주'},
            {'type': 'table', 'table': {'rows': 1, 'cols': 1, 'hasHeader': False, 'cells': [[
                cell('중첩 내용', blocks=[{'type': 'table'}, {'type': 'image'}]),
            ]]}},
            {'type': 'image', 'imageData': {'sha256': 'abc', 'byteLength': 10}},
        ]}
        blocks, warnings = kordoc_to_blocks(document)
        self.assertEqual([block.get('text') for block in blocks[:2]], ['본문', '각주'])
        self.assertTrue(any('이미지 메타데이터' in message for message in warnings))
        self.assertTrue(any('중첩표' in message for message in warnings))
        self.assertTrue(any('글꼴' in message for message in warnings))
        self.assertTrue(any('하이퍼링크' in message for message in warnings))

    def test_lists_heading_and_separator_follow_source_order(self):
        blocks, _ = kordoc_to_blocks({'blocks': [
            {'type': 'heading', 'level': 6, 'text': '제목'},
            {'type': 'list', 'text': '하나', 'listDepth': 2, 'children': [
                {'type': 'list', 'text': '둘'},
            ]},
            {'type': 'separator'},
        ]})
        self.assertEqual([block['type'] for block in blocks], ['h', 'li', 'li', 'hr'])
        self.assertEqual(blocks[0]['level'], 3)
        self.assertEqual(blocks[1]['depth'], 2)

    def test_native_extensions_are_unchanged_and_new_formats_require_opt_in(self):
        self.assertNotIn('.hwpx', converter.SUPPORTED_EXTENSIONS)
        self.assertTrue({'.hwpx', '.hwp', '.hwpml', '.xls', '.pptx'} <= KORDOC_INPUT_EXTENSIONS)
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'document.hwpx'
            source.write_bytes(b'fixture')
            with self.assertRaises(ValueError):
                converter.detect_and_parse(source)
            with patch.object(converter, 'parse_kordoc_document', return_value=[{'type': 'p', 'text': '본문'}]) as parse:
                self.assertEqual(converter.detect_and_parse(source, input_engine='kordoc')[0]['text'], '본문')
                parse.assert_called_once_with(source, package_dir=None)

    def test_backend_unavailable_fails_only_optional_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'document.hwpx'
            source.write_bytes(b'fixture')
            with patch('kordoc_client.KordocClient.request', return_value={
                'ok': False, 'status': 'error', 'error': {'message': 'not installed'},
            }):
                with self.assertRaisesRegex(RuntimeError, 'not installed'):
                    converter.detect_and_parse(source, input_engine='kordoc')
        self.assertEqual(converter.parse_markdown('기존 본문'), [{'type': 'p', 'text': '기존 본문'}])

    def test_optional_partial_response_keeps_loss_warning(self):
        converter.pop_conversion_notes()
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'document.hwpx'
            source.write_bytes(b'fixture')
            with patch('kordoc_client.KordocClient.request', return_value={
                'ok': False, 'status': 'partial', 'data': {'blocks': [{'type': 'paragraph', 'text': '추출'}]},
                'warnings': [{'code': 'READ_WARNING', 'message': '비공개 문서 발췌'}], 'error': None,
            }):
                blocks = converter.detect_and_parse(source, input_engine='kordoc')
        self.assertEqual(blocks, [{'type': 'p', 'text': '추출'}])
        notes = converter.pop_conversion_notes()
        self.assertTrue(any('일부 읽기' in note for note in notes))
        self.assertIn('READ_WARNING', '\n'.join(notes))
        self.assertNotIn('비공개 문서 발췌', '\n'.join(notes))

    def test_conversion_rejects_same_source_before_com(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'original.hwpx'
            path.write_bytes(b'original')
            with self.assertRaisesRegex(ValueError, '덮어쓸 수 없습니다'):
                converter.convert_file(None, path, path, input_engine='kordoc')
            self.assertEqual(path.read_bytes(), b'original')

    def test_output_cleanup_cannot_delete_selected_hwpx_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'original.hwpx'
            source.write_bytes(b'original')
            converter.write_output_manifest(root, ['original.hwpx'])
            with patch.object(converter, 'create_hwp_object') as com:
                with self.assertRaisesRegex(ValueError, '입력 원본'):
                    converter.main([str(source), '-o', str(root), '--empty-output-folder', '--input-engine', 'kordoc'])
                com.assert_not_called()
            self.assertEqual(source.read_bytes(), b'original')

    def test_list_formats_exposes_explicit_engine(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(converter.main(['--input-engine', 'kordoc', '--list-formats']), 0)
        self.assertIn('.hwpx', output.getvalue())


if __name__ == '__main__':
    unittest.main()
