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

## 2026-08-26 Track E — 위생 정리(E-1·E-3·E-4) + COM 잔여 검증 재개(E-2)

### E-3 편집기 안전성 게이트 상설화
- `python-hwpx` 설치 버전이 2.8.3(08b2130 검증 시 사용된 6.0.2의 `editor_safety_gate` CLI는 이 버전에 없음).
- 동등한 목적을 달성하는 `scripts/hwpx_editor_safety_gate.py` 신설 — `hwpx.tools.package_validator.validate_package`(ZIP·컨테이너·매니페스트 구조) + `hwpx.tools.validator.validate_document`(header/section OWPML 스키마)를 조합.
- 번들 샘플 2종(`samples/sample.md`, `samples/sample_complex.md`) 실변환 산출물에 대해 실행: 둘 다 **PASS**(경고 1건 — manifest version part 미참조, 엔진이 `version.xml`로 fallback. `--strict` 지정 시 동일 입력이 FAIL로 전환되는 것도 확인).

### E-4 스테일 QA 잔재 정리
- `native-qa.txt`는 `anyway_to_hwpx_gui.py` 워크트리 부재 시점의 구 `ModuleNotFoundError` 트레이스백(mojibake)이었음 — 현재 GUI 소스가 존재하여 무효.
- `tests/gui_state_harness.py`를 7개 상태(default/valid-drop/invalid-drop/busy/success/warning/error) 전부 재실행 — **exit 0, 예외 없음**. 로그를 실측 결과로 갱신.

### E-1 UPX 재설치 후 exe 재압축
- winget으로 UPX 5.2.0 설치(사용자 승인 후 진행).
- `python -m PyInstaller --clean --noconfirm anyway_to_hwpx_gui.spec` 재빌드: **81,276,499 → 73,746,619 bytes**(77.5MB → 70.3MB).
- 5초 기동 smoke: 프로세스 정상 유지 확인 후 정상 종료.

### E-2 COM 의존 잔여 검증 재개 — 신규 결함 발견
- `python anyway_to_hwpx_com.py --preflight`: OK.
- `HWPX_RUN_COM_TESTS=1 python -m unittest ... test_pdf_hwp_com_integration.py`: **이번이 이 테스트의 최초 실제 실행**(과거 세션은 전부 COM timeout으로 미실시, handoff.md 기록).
- 1차 실행 → `hwp.Open(str(hwpx))` 단일 인자 호출이 COM 오류(`매개 변수의 개수가 잘못되었습니다`)로 실패. COM 타입라이브러리 조회 결과 `Open(filename, Format, arg)` 3개 필수 인자(cParamsOpt=0). 코드베이스 내 유일한 `.Open()` 호출이며, `SaveAs`는 이미 3-인자 관례(`hwp.SaveAs(path, 'HWPX', 'lock:false')`, anyway_to_hwpx_com.py:2870)를 따르고 있어 **변환기 자체의 회귀가 아니라 테스트 코드의 API 호출 결함**으로 판정. `tests/test_pdf_hwp_com_integration.py`의 `Open`/`SaveAs` 호출을 3-인자로 수정.
- 수정 후 재실행 → COM Open/SaveAs는 정상 동작하나 **새로운 실패**: 원본 PDF와 왕복 재추출 PDF의 비백색 콘텐츠 경계가 크게 어긋남.
  - 페이지 크기: 595×842pt → 595×841pt (거의 동일).
  - 콘텐츠 경계: 원본 `(71, 119, 520, 300)` → 재추출 `(155, 217, 594, 400)`. 박스 크기(약 449×181 → 439×183)는 유지되나 **우측·하단으로 84~98pt 균일 이동**.
  - `configure_pdf_page_setup()`(anyway_to_hwpx_com.py:2351)이 여백을 전부 0으로 설정하고 `insert_pdf_page_image()`(:2376)가 `hwp.InsertPicture`로 이미지를 삽입하지만, **`SaveAs`로 PDF 재추출하는 과정에서 콘텐츠 위치가 밀리는 현상**으로 추정(원인 미확정 — HWP PDF 익스포트가 0-여백 섹션을 그대로 반영하지 않거나, `InsertPicture` 앵커가 페이지 좌상단(0,0)에 고정되지 않을 가능성).
  - **이 테스트가 과거 한 번도 끝까지 실행된 적이 없어 지금까지 미검출 상태였음.** 기존 HWPX 산출물 자체의 구조 계약(`_assert_hwpx_image_contract` — pic/orgSz/curSz/sz)은 별도로 통과하므로, 결함은 HWPX 산출물이 아니라 **PDF 재추출(SaveAs 'PDF') 경로** 또는 그 왕복 비교 자체의 특성일 수 있음 — 근본 원인 확정에는 추가 조사 필요.
- 이 발견은 Track E 범위(위생 정리) 밖의 신규 항목이라 IMPROVEMENT_PLAN.md에 별도 항목(E-7)으로 등록. 사용자 승인 후 원인 조사를 이어감(아래).
- 전체 COM-불요 스위트(243 tests) 재확인: 변경 없이 green.

### E-7 근본 원인 규명·수정(TDD, `superpowers:systematic-debugging` + `superpowers:test-driven-development` 적용)

**Phase 1 — 증거 수집(레이어별 경계 계측)**:
- L1 원본 PDF 픽스처 비백색 경계: `(71, 119, 520, 300)`(fitz 기본 렌더).
- L2 중간 산출물(`pdf_layout.render_pdf_layout`, LAYOUT_DPI=200) PNG 비백색 픽셀 경계를 pt로 환산: `(70.92, 118.8, 520.92, 300.96)` — **원본과 사실상 동일**(렌더링 단계는 무결).
- L3 HWPX `section0.xml`의 `pic` 요소: `offset={x:0,y:0}`, `pos.horzOffset/vertOffset=0` — **이미지 자체는 앵커 원점(0,0)에 정확히 배치됨**. 그러나 같은 파일의 `pagePr/margin` = `{left:8504, right:8504, top:5668, bottom:4252, header:4252, footer:4252}`(HWPUNIT) — **`configure_pdf_page_setup()`이 의도한 0이 아니라 HWP 기본 여백(30/20/15/15mm)이 그대로 저장됨**.
- 최소 재현: `hwp.CreateAction('PageSetup')` → `action.CreateSet()` → `page_def.SetItem('LeftMargin', 1234)` → `action.Execute(parameter_set)`(반환값 `True`) 직후, **동일 세션에서 새 `CreateAction('PageSetup')`으로 재조회하면 여전히 기본값(8504) 그대로**임을 확인 — `Execute`가 "성공"을 반환하지만 여백 항목에는 실제로 아무 효과가 없는 HWP COM 동작.
- 정량 검증: 좌측 여백 8504 HWPUNIT ≈ 30.0mm ≈ 85.04pt(관측 x축 어긋남 84pt와 일치). 상단 여백(5668≈20mm≈56.7pt) + 헤더 영역(4252≈15mm≈42.5pt) 합 ≈ 99.2pt(관측 y축 어긋남 98~100pt와 일치). **여백+헤더 미제거가 어긋남의 전체를 정량적으로 설명**.

**Phase 3 — 가설·최소 검증**: "`hwp.CreateAction('PageSetup')` 경로가 아니라 `hwp.HParameterSet.HSecDef` + `hwp.HAction.GetDefault/Execute('PageSetup', sec.HSet)`(속성 접근 방식) 경로를 쓰면 여백이 실제로 반영될 것이다." → 동일 세션에서 두 경로를 직접 비교 실행, 후자만 재조회 시 0으로 반영됨을 확인(두 가지 독립 재조회 방식으로 교차 확인).

**Phase 4 — TDD 수정**:
- RED: `tests/test_pdf_hwp_image_writer.py`에 새 계약 테스트(`test_page_setup_uses_hparameterset_secdef_and_source_geometry` 등, `_FakeHwp`에 `HParameterSet.HSecDef`/`_FakePageDef` 페이크 추가) 작성 — 옛 구현 대상 실행 시 3건 FAIL(예상된 이유: `PageDef` 속성이 `None`으로 남음·예외 테스트가 잘못된 경로를 패치).
- GREEN: `configure_pdf_page_setup()`(anyway_to_hwpx_com.py)을 `hwp.HParameterSet.HSecDef` 속성 접근 패턴으로 재작성. 재실행 시 16/16 green.
- 회귀 확인: `python -m unittest discover -s tests` → 243 passed, 1 skipped(변경 없음).
- 실COM 재검증: `HWPX_RUN_COM_TESTS=1 python -m unittest discover -s tests -p "test_pdf_hwp_com_integration.py"` → **ok**(1 test, 1584.6s). **이 테스트가 생성된 이래 최초로 통과** — round-trip 위치 어긋남 결함 완전 해소 확인.
