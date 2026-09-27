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

## 2026-09-27 Track F 웨이브 1 — 경고 가시화(F-2)·배포 정상화 준비(F-1)

- TDD: Task 1~6 각각 RED(예상 사유 확인) → GREEN. `python -m unittest discover -s tests` → **258 tests OK, skipped=1**(skip = `HWPX_RUN_COM_TESTS` 미설정 COM 게이트, bs4 4.14.3 설치 확인).
- `python -m py_compile anyway_to_hwpx_com.py anyway_to_hwpx_gui.py table_hwpx_postprocess.py gui_conversion_worker.py gui_input_status.py`: pass. 경고 `print` 잔존 0곳(grep).
- GUI 상태 하네스 7개 상태(`--hold-seconds 0.2`): 전부 exit 0.
- `--preflight`: OK. 실COM 변환 `tests/out/track-f/wave1_check.md --insert-end-mark`(표 2개·alt 이미지 1개·링크 1개): exit 0, stderr note 3건 각 1회 — `[확인 필요] Markdown 이미지 1개 미삽입`, `[참고] Markdown 링크 1개`, `[참고] 표 열 너비 … TableColWidth 미지원`(표 2개에 1회), `[경고]` 0건.
- `scripts/hwpx_editor_safety_gate.py`: PASS(경고 1건 — manifest version part 미참조, 기존과 동일).
- 실물 검증 스크립트(산출물 XML + 한글 `Open(path,'HWPX','')` → `SaveAs(pdf,'PDF','')` → PyMuPDF 1쪽 렌더) 11/11 PASS: mimetype 첫 엔트리 STORED, alt·URL 부재, 여백 7087/5669/7087/7087/2835/2835, 본문 참조 paraPr(20~23) 줄 간격 160%, 표 2개 rowCnt/colCnt·머리글 header=1, 재열람·PDF 저장 성공. 렌더 PNG 육안 확인(글리프·여백·표 음영·이중선 정상).
  - 최초 판정에서 줄 간격 1건 FAIL은 검증 기준 오류였음: 미사용 기본 스타일 paraPr(9·10·11·19)의 switch 내부 값 150/130을 포함해 판정. 본문 참조 paraPr 기준으로 교정 후 PASS. 후처리가 직계 `lineSpacing`만 갱신하는 동작은 기록(렌더 영향 없음).
- 릴리스 후보 판독(실행 없음): 디스크 exe blob `2a61e81` = `c5438a8` 추적 blob, 73,746,447 bytes, SHA-256 `9369b286f1ed9bf23fe57c1f994181522ce151068820c57f6e8888554e818824`. CArchive 항목 `anyway_to_hwpx_com.pyc`(PYZ 아님) 역직렬화 결과 `HSecDef` 포함 → E-7 수정 반영 확인.
- NOT_RUN: 실COM PDF layout 통합 테스트(약 26분) — layout 경로 변경은 note 합류 1줄, 단위 테스트로 확인.

### 릴리스 전 exe 기동 확인 — FAIL(N15), 릴리스 중단

- 방법: exe 실행 후 보이는 최상위 창을 1초 간격으로 전수 기록(프로세스·클래스·제목), 메인 창 출현 시 `WM_CLOSE`로 정상 종료. 대조군(소스 GUI `python anyway_to_hwpx_gui.py`)은 6.2s에 `TkTopLevel` "HWPX 변환기" 출현·WM_CLOSE exit 0 → 판정 방법 유효.
- `dist/anyway_to_hwpx_gui.exe`(`c5438a8`): 18~21s에 자식 프로세스가 `#32770` "Unhandled exception in script" 대화상자 표시, 60s 내 메인 창 없음. 대화상자 원문: `Failed to execute script 'pyi_rth__tkinter' … FileNotFoundError: Tcl data directory "…\_MEI…\_tcl_data" not found.` 확인 후 프로세스 트리 종료, 잔여 프로세스 없음.
- 이력 판독(실행 없음, 임시 파일 자동 삭제): `83103a7`·`ef4229f`·`4b6c5ae`·`8812a11`·`c6e91df` = `tcl86t.dll`·`tk86t.dll` + `_tcl_data` 832개·`_tk_data` 89개 / `c5438a8` = `tcl90.dll`·`tcl9tk90.dll` + 0·0개.
- 빌드 환경: Python 3.14.7, Tcl/Tk 9.0.4, `info library` = `//zipfs:/lib/tcl/tcl_library`(DLL 내장), `base_prefix\tcl` 없음, PyInstaller 6.20.0 `tcl_tk` 훅에 zipfs 처리 없음, 설치 Python 1개.
- 결론: 08-06 이후 Python 업데이트로 Tcl 9가 되면서 이 환경의 모든 onefile 빌드가 기동 불가. 2026-08-26 E-1 "5초 기동 smoke 통과"는 오류 대화상자가 떠 있는 동안의 프로세스 생존을 본 거짓 통과로 판단. 공개 `v2026.08.06`(`c6e91df`, Tcl 8.6)은 영향 없음.

### D-11 ① 시험 작업 — Tcl/Tk 9 zipfs 라이브러리 번들 (PASS)

- 확인: 런타임 훅 `pyi_rth__tkinter`는 `_tcl_data`·`_tk_data` 둘 다 요구, 빌드 훅은 `info library`가 `//zipfs:` 경로라 수집 생략. zipfs 실측 — Tcl `//zipfs:/lib/tcl/tcl_library`(tcl90.dll, 869항목), Tk `//zipfs:/lib/tk/tk_library`(tcl9tk90.dll, 94항목, Tk 로드 후 마운트).
- 수정(브랜치 `spike/tcl9-bundle`): `anyway_to_hwpx_gui.spec`의 `_tcl_tk_zipfs_datas()` — 숨김 Tk로 두 경로를 조회해 모두 zipfs일 때만 `workpath/tcl_tk_zipfs`에 `file copy` 후 `_tcl_data`·`_tk_data`로 datas 추가.
- 빌드: `HWPX_GUI_PDF_STACK=full python -m PyInstaller --clean --noconfirm --distpath C:/tmp/hwpx-gui-tcl9-spike/dist --workpath C:/tmp/hwpx-gui-tcl9-spike/work anyway_to_hwpx_gui.spec` → exit 0, 75,106,019 bytes, SHA-256 `53ebe0775ab0e6b005b7fc274f9dda0355779ebda8b488405af0d2d71809b528`. UPX 실패 3건(arm64 tkdnd DLL CantPack, `_uuid.pyd`·`python3.dll` NotCompressible)은 비압축 포함.
- 판독: `_tcl_data` 839·`_tk_data` 90개, `init.tcl`·`tk.tcl`·`encoding` 83개. 내장 `anyway_to_hwpx_com.pyc`에 `HSecDef`(E-7)·웨이브 1 문구 존재, 구 문구 부재.
- 기동 확인(창 감지형) 2회: 메인 창 `TkTopLevel` "HWPX 변환기" 12.4s·25.6s 출현, `#32770` 없음, `WM_CLOSE` exit 0, 잔여 프로세스 없음. 추가 유지 확인 1회: 13.6s 창 출현 → 5초 후 프로세스·창 유지 → `WM_CLOSE` exit 0. onefile 기동 시간 12~26s 관찰.
- `scripts/packaging_smoke.ps1` 기본 모드는 import 검사만(spec 미평가) — 새 spec 영향 없음. `-Build` 모드는 위 빌드와 같은 명령.
- 미실행: 동결 exe로 실제 GUI 변환 1건(스파이크 합격 기준 밖) — 발행 전 권장.

### 채택 후 동결 exe GUI 변환 확인 (2026-09-27, 화면 조작)

- 스파이크를 로컬 `main`에 `--no-ff` 병합(`ccd76bd`, 빌드 입력 트리 = `9ce4944`). 테스트 258 OK.
- 화면 조작(앱 접근 승인: 테스트 exe·한글 2020): "파일 추가" → `C:\tmp\hwpx-gui-tcl9-spike\gui-test\wave1_check.md` 입력 → 저장 폴더 자동 지정 → "변환 시작". Tk 버튼은 마우스 클릭만으로 동작하지 않아 포커스 후 Space로 실행(자동화 입력 특성).
- 변환 중 한글이 `C:\tmp\…\wave1_check.hwpx` 파일 접근 확인 창 표시 → "접근 허용(Y)" 1회(모두 허용 아님).
- 결과: 로그 `변환 중 → 완료` + `[확인 필요] Markdown 이미지 1개 미삽입…`(빨강) + `[참고]` 2건(회색), 상태 "변환 완료 1개 · 확인 필요 1개 — 로그를 확인하세요", 대화상자 "변환 완료(확인 필요)"(대상 `wave1_check.md`) → "아니요". 창 `WM_CLOSE` 후 exe·한글 잔여 프로세스 없음.
- 산출물 `wave1_check.hwpx`(26,449 bytes) 구조 검증 7/7 PASS(mimetype·alt/URL 부재·여백·본문 줄 간격 160%·표 머리글·안전 게이트).
- 비교 시도: 같은 원고를 Python CLI로 `C:\tmp\…\gui-test\out` 저장 → `SaveAs` 실패(exit 1). 직후 화면에 다른 문서(ice-plan-studio HWPX)가 한글에서 열려 있어 동시 사용과 겹쳤을 가능성 → 판정 불가, 재시험 필요(N16). 그 창은 조작하지 않음.
- 보류: 저장본 한글 재열람(한글이 다른 작업에 사용 중).
