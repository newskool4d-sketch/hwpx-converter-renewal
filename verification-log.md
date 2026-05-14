# anyway_to_hwpx_com verification log

## Syntax and CLI

- `python -m py_compile C:/Users/홍주형/.claude/hwpx-converter-renewal/anyway_to_hwpx_com.py`: pass.
- `python anyway_to_hwpx_com.py --list-formats`: supported extensions are `.csv`, `.docx`, `.htm`, `.html`, `.md`, `.pdf`, `.txt`, `.xlsx`.

## Parser smoke checks

- `.md`: pass — heading, official header, table, list blocks detected.
- `.txt`: pass — paragraph and list blocks detected.
- `.html`: pass — heading, paragraph, table blocks detected.
- `.csv`: pass — table block detected.
- `.xlsx`: pass — worksheet heading and table block detected.

## PDF verification

- PDF route implemented as kordoc-first.
- Fallback uses `pypdf` when available.
- OCR/scanned PDF quality remains dependent on kordoc/Tesseract availability.

## HWP COM conversion

- `sample.md` converted to `C:/Users/홍주형/.claude/hwpx-converter-renewal/out/sample.hwpx`.
- Conversion completed with warning: `열 너비 조정 실패: 'NoneType' object has no attribute 'CreateSet'`.

## Remaining table follow-up

- CSV/XLSX/HTML table blocks are routed to the existing `insert_table()` implementation.
- Detailed table width, alignment, merged-cell, and multi-sheet formatting behavior requires separate review after this renewal pass.
- Current known table issue: HWP COM `TableColWidth` action may return `None` in this environment, producing a warning while still allowing conversion to complete.

## 2026-05-14 Fix pass

- `calc_col_widths()` no longer returns negative widths for wide tables. Checked 1, 2, 8, 9, 10, 12, and 20 column cases; every result had positive widths and summed to `14000`.
- `insert_table()` now treats missing `TableColWidth` action as a recoverable warning and moves back toward the first cell before inserting table contents. Checked with a fake HWP COM object where `TableColWidth` returns `None`.
- `parse_html()` now preserves `li` blocks, including nested list depth, and avoids duplicate parsing inside `blockquote`, `pre`, and `li`.
- `parse_xlsx()` now closes the workbook in `finally`.
- `python -m py_compile anyway_to_hwpx_com.py`: pass.
- Actual HWP COM conversion could not be rerun in this session because `win32com.client.Dispatch('HWPFrame.HwpObject')` failed with COM server startup error `서버 실행이 실패했습니다.` No lingering HWP/Hancom process was detected afterward.

## 2026-05-14 Table layout heuristic pass

- Replaced simple max-text based table width calculation with content-type heuristics for index, number/amount, date, name, position, organization, title, detail, and generic columns.
- Added East Asian width based visual text measurement via `unicodedata.east_asian_width()` to better account for Korean/CJK full-width text.
- Added `calc_row_heights()` to estimate row height from final column widths and expected wrapping line counts.
- `insert_table()` now passes calculated total width/height hints through `WidthValue` and `HeightValue` when the HWP COM action accepts them.
- `python -m py_compile anyway_to_hwpx_com.py`: pass.
- `python anyway_to_hwpx_com.py --list-formats`: pass.
- Manual layout smoke case with headers `번호/소속/성명/직위/사업명/기간/예산/추진내용/비고`: widths summed to `14000`; row heights were `[1500, 2740]`.
- Actual sample HWPX conversion still could not be rerun because `win32com.client.Dispatch('HWPFrame.HwpObject')` failed with COM server startup error `서버 실행이 실패했습니다.` No lingering HWP/Hancom process was detected afterward.

## 2026-05-14 Preservation defaults pass

- `build_output_path()` now avoids overwriting existing HWPX files by appending ` - 2`, ` - 3`, etc.
- Automatic `끝` insertion is no longer part of the default conversion path. It is available only with `--insert-end-mark`.
- `insert_table()` now tracks actual right-cell moves during column-width adjustment and only moves back by that count when recovering from `TableColWidth` failures.
- `python -m py_compile anyway_to_hwpx_com.py`: pass.
- `python anyway_to_hwpx_com.py --help`: pass, including `--insert-end-mark`.
- Output-path collision check with existing `sample.hwpx` and `sample - 2.hwpx`: returned `sample - 3.hwpx`.
- Fake HWP table cursor checks: normal width adjustment moved back 2 cells for 3 columns; early and mid-loop failures moved back only the actual prior right-cell moves.

## 2026-05-14 GUI EXE pass

- Added `anyway_to_hwpx_gui.py` as a Tkinter wrapper around `anyway_to_hwpx_com.py`.
- GUI flow: select source files, select output folder, optionally enable `끝` insertion, then convert through HWP COM.
- `python -m py_compile anyway_to_hwpx_gui.py`: pass.
- GUI module import check: pass.
- Built one-file windowed executable with PyInstaller 6.20.0.
- Output: `dist/anyway_to_hwpx_gui.exe` (39,389,019 bytes).
- PyInstaller warning review: most missing modules are optional/platform-specific; `pypdf` is not bundled, so PDF fallback still depends on available local PDF extraction support.

## 2026-05-14 PDF-enabled GUI EXE pass

- Extended `extract_pdf_text_fallback()` to try `pdfplumber`, then `PyMuPDF(fitz)`, then optional `pypdf`.
- Updated `dist/사용방법.txt` with prerequisite guidance: required Hancom HWP, recommended VC++ redistributable, PDF/OCR notes, and developer rebuild dependencies.
- `python -m py_compile anyway_to_hwpx_com.py anyway_to_hwpx_gui.py`: pass.
- Created a small text PDF with PyMuPDF and verified `parse_pdf()` extracted text into blocks.
- Rebuilt `dist/anyway_to_hwpx_gui.exe` with hidden imports for `pdfplumber`, `fitz`, and `pymupdf`.
- Output: `dist/anyway_to_hwpx_gui.exe` (88,463,793 bytes).
- PyInstaller warnings still list optional `pypdf` and PyMuPDF optional modules; text PDF extraction is covered by bundled `pdfplumber`/`PyMuPDF`, while scanned image PDFs still need OCR.
