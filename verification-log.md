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

## 2026-05-23 Reliability improvement pass

- Added `requirements.txt` for reproducible development and rebuild setup.
- Added `--preflight` to check HWP COM startup before conversion.
- Moved HWP COM startup into `create_hwp_object()` so CLI and GUI share the same startup and error-message path.
- Changed HWP COM preflight to run in a child worker process with a 45-second timeout, preventing raw tracebacks on COM startup failure.
- Added `--kordoc-home` and `KORDOC_HOME` / `KORDOC_AI_HOME` support for configurable scanned-PDF OCR paths.
- Added COM-free unit tests for Markdown/plain-text parsing, output path collision handling, table width/height heuristics, and OCR path resolution.
- Improved GUI failure dialog so the first failed target and error message are visible without digging through the log.
- Updated README with user/developer sections, preflight usage, OCR configuration, setup, tests, and build commands.
- `python -m py_compile anyway_to_hwpx_com.py anyway_to_hwpx_gui.py`: pass.
- `python -m unittest discover -s tests`: pass, 7 tests.
- `python anyway_to_hwpx_com.py --help`: pass, includes `--preflight` and `--kordoc-home`.
- `python anyway_to_hwpx_com.py --list-formats`: pass.
- `python anyway_to_hwpx_com.py --preflight`: exits cleanly with `[FAIL] HWP COM preflight timed out after 45 seconds.` in the current environment. The temporary `Hwp` process exited shortly afterward.

## 2026-05-23 GUI EXE rebuild after reliability pass

- Rebuilt `dist/anyway_to_hwpx_gui.exe` with PyInstaller 6.20.0 and Python 3.14.3.
- Build command: `python -m PyInstaller --onefile --windowed --name anyway_to_hwpx_gui --clean --hidden-import=pdfplumber --hidden-import=fitz --hidden-import=pymupdf .\anyway_to_hwpx_gui.py`
- Output: `dist/anyway_to_hwpx_gui.exe` (90,804,771 bytes).
- PyInstaller warning file reviewed at `build/anyway_to_hwpx_gui/warn-anyway_to_hwpx_gui.txt`; listed modules are mostly optional, platform-specific, or conditional imports from bundled dependencies.
- `python -m py_compile anyway_to_hwpx_com.py anyway_to_hwpx_gui.py`: pass.
- `python -m unittest discover -s tests`: pass, 7 tests.

## 2026-06-08 HWP COM sample gate and lightweight EXE rebuild

- HWP COM hidden preflight command: `python anyway_to_hwpx_com.py --preflight`.
- Hidden preflight result: fail, `[FAIL] HWP COM preflight timed out after 45 seconds.`
- HWP COM visible preflight command: `python -c "import anyway_to_hwpx_com as m; print(m.run_hwp_preflight(visible=True, timeout=90))"`.
- Visible preflight result: fail, `RuntimeError: HWP COM preflight timed out after 90 seconds.`
- Actual HWPX sample conversion was not run after the failed preflight because the COM startup gate did not pass.
- Rebuilt EXE with the feature-preserving lightweight spec: `python -m PyInstaller --clean --noconfirm anyway_to_hwpx_gui.spec`.
- New output: `dist/anyway_to_hwpx_gui.exe` (79,728,480 bytes, 76.04 MiB).
- Previous large baseline kept for comparison: `dist/anyway_to_hwpx_gui ver 4.exe` (363,749,849 bytes, 346.90 MiB).
- Size change: -284,021,369 bytes (-270.86 MiB), 78.08% smaller.
- Existing PDF/ODL/HWP conversion features were kept in the spec; actual HWP COM visual rendering still requires a Hancom HWP environment where preflight completes.

## 2026-06-09 HWP COM preflight 복구 + 열너비 비율 버그 수정

- `python anyway_to_hwpx_com.py --preflight`: `HWP COM preflight OK: HWPFrame.HwpObject 생성 및 SecurityModule 등록 성공` — 이전 세션 타임아웃 문제 해결됨.
- `python anyway_to_hwpx_com.py samples/sample.md -o out`: 변환 완료. `[경고] 열 너비 조정 실패: TableColWidth action unavailable` 경고는 유지되나 XML 후처리가 이를 보완함.
- HWP COM 조사 결과 `TableColWidth` 액션이 이 버전에서 사용 불가. `TableCreate WidthValue` 설정도 무시되며 항상 기본 텍스트 영역 너비(41954 hwpUnit)로 생성됨.
- 버그: `COLUMN_PROFILES` min/max가 TABLE_TOTAL_WIDTH=14000 기준 고정값이어서 41954 너비 표에 적용 시 열 비율이 왜곡됨 (예: ['항목','값'] → 4.5%:95.5%).
- 수정 1 — `hwpx_layout.py` `_infer_col_kind`: 헤더가 있는 컬럼은 'name' 폴백 분류 제거 (`not header_text` 조건 추가).
- 수정 2 — `hwpx_layout.py` `_redistribute_widths`: `scale` 파라미터 추가 (`total / TABLE_TOTAL_WIDTH`), min/max를 scale에 비례 적용.
- 수정 3 — `hwpx_layout.py` `calc_col_widths`: scale 계산 후 `_redistribute_widths`에 전달, pref도 scale 적용.
- `python -m py_compile anyway_to_hwpx_com.py anyway_to_hwpx_gui.py hwpx_layout.py`: pass.
- `python -m unittest discover -s tests -q`: `Ran 26 tests ... OK` (신규 2개 추가: `test_column_widths_scale_to_large_table_width`, `test_column_widths_scale_proportionally_across_totals`).
- 실제 변환 검증: `samples/sample.md` → `out/sample - 3.hwpx`, 열 비율 28.0%:72.0% (기대: 28:72) ✓.
