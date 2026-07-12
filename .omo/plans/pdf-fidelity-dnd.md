# pdf-fidelity-dnd - Work Plan

## TL;DR (For humans)
**What you'll get:** PDF는 원본 페이지 모양을 우선 보존하거나, 필요할 때 편집 가능한 구조로 변환할 수 있습니다. 파일 목록의 빈 영역과 목록 안에 파일을 여러 개 놓아 추가할 수 있고, 화면은 IBM Carbon 계열의 명확한 상태 중심 디자인으로 바뀝니다.

**Why this approach:** PDF를 텍스트로 재조립하면 원래 배치를 보장할 수 없으므로, 기본값은 페이지 이미지를 HWPX에 넣는 레이아웃 모드입니다. 편집이 필요할 때만 기존 구조 파싱을 고르게 하며, 변환 중 목록 변경으로 생길 수 있는 오류도 함께 막습니다.

**What it will NOT do:** 레이아웃 모드에서 텍스트까지 완전 편집 가능하게 만들거나, 클라우드 OCR로 파일을 외부에 전송하지 않습니다. 페이지 크기가 섞인 PDF는 왜곡해서 변환하지 않습니다.

**Effort:** Large
**Risk:** High - HWP COM 그림 삽입, 네이티브 드롭 런타임, 실행 파일 패키징을 실제 Windows 환경에서 함께 검증해야 합니다.
**Decisions to sanity-check:** PDF 기본값은 레이아웃 우선, 렌더 품질은 200 DPI와 500 MiB 보호 한도, UI는 IBM Blue·완료 Green·주의 Yellow·오류 Red를 상태별로 사용합니다.

Your next move: 실행을 시작하거나, 구현 전 고정밀 계획 검토를 요청하세요. Full execution detail follows below.

---

> TL;DR (machine): Large/high-risk plan for layout-first PDF image conversion, editable fallback, file-list-only native drops, and IBM Carbon four-color Tkinter UI.

## Scope
### Must have
- PDF의 기본 변환 방식을 `layout`으로 바꾼다. 이 방식은 PyMuPDF로 각 페이지를 200 DPI PNG로 렌더링하고, HWP COM으로 물리 크기를 유지한 그림 페이지로 삽입한다.
- 기존 구조 추출 경로는 `editable` 모드로 보존한다. GUI와 CLI에 같은 이름의 선택값을 제공하고, `convert_file()` 호출도 명시적 인자로 모드를 전달한다.
- 파일 목록 컨테이너의 빈 부분과 실제 `Listbox`를 OS 파일 드롭 타깃으로 등록한다. 파일 선택 대화상자와 드롭은 같은 입력 정규화 함수를 쓴다.
- IBM Carbon 계열의 `DESIGN.md`와 Tkinter 토큰 모듈을 만든다. IBM Blue, Success Green, Warning Yellow, Error Red의 네 가지 유채색을 기능 상태에만 사용한다.
- 변환 중 입력 목록, 저장 폴더, 모든 옵션과 PDF 모드 변경을 잠그고, worker에는 입력 목록의 불변 사본을 전달한다.
- `opendataloader-pdf`, Java 11+, `tkinterdnd2`, PyInstaller의 수집 결과를 진단하고 문서화한다.
- PDF build stack 계약을 고정한다: `full`은 layout + ODL editable, `text`는 layout + pdfplumber/PyMuPDF/pypdf editable, `none`은 PDF 입력 전체 비활성화다. 런타임은 `importlib.util.find_spec()` 기반 capability 객체로 실제 번들 상태를 판정한다.
- 편집 가능한 `editable` 출력의 기본 문서 서식은 줄간격 160%, 문단 아래 간격 2로 고정하고, 글자 장평·자간은 기본값을 유지한다. 줄바꿈 시 명사와 연결되는 조사가 분리·잘리지 않도록 한국어 어절/조사 단위의 줄바꿈을 보장한다. 원본 페이지 이미지를 삽입하는 `layout` 모드에는 이 서식을 적용하지 않는다.
### Must NOT have (guardrails, anti-slop, scope boundaries)
- PDF 레이아웃 모드에 편집 가능한 텍스트 오버레이, 새 클라우드 OCR/PDF 서비스, 외부 전송을 추가하지 않는다.
- HWPX ZIP/XML을 직접 조립하거나 편집해 그림을 넣지 않는다. 그림 삽입은 HWP COM으로만 수행한다.
- 레이아웃 모드 출력에 공문서 여백·표·목록·줄간격 XML 후처리를 적용하지 않는다.
- 혼합 페이지 크기/방향 PDF를 억지로 스케일링하지 않는다. 실행 전에 거부하고 `editable` 모드를 안내한다.
- IBM의 로고·마케팅 콘텐츠를 복사하지 않고, 제시된 IBM 디자인 문서의 토큰·상태·평면 사각형 원칙만 활용한다.
- 파일 목록 이외의 헤더 버튼, 저장 폴더 입력, 로그 영역을 드롭 타깃으로 만들지 않는다.

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: **TDD** + Python `unittest`; COM이 필요한 검증은 `HWPX_RUN_COM_TESTS=1`일 때만 실제 HWP COM으로 실행한다.
- Every task writes its command output, generated fixture paths, screenshots, or XML assertions to `.omo/evidence/task-<N>-pdf-fidelity-dnd.md`.
- Before any implementation or commit, run `git rev-parse --show-toplevel` and `git status --short`; require the expected repository root and protect the current unrelated dirty paths `dist/Anyway_to_hwpx(2026. 6. 11.).zip`, `gui_preview.png`, and `samples/sample_complex.md`. If the command is not inside this Git repository, stop before editing.
- COM-free gate: `python -m unittest discover -s tests` and `python -m py_compile anyway_to_hwpx_com.py anyway_to_hwpx_gui.py pdf_layout.py gui_file_intake.py ui_design.py`.
- HWP COM gate: `python anyway_to_hwpx_com.py --preflight`, then run the new `HWPX_RUN_COM_TESTS=1` round-trip suite. It must assert page count, `hp:pagePr` width/height and zero margins, one `hp:pic` per page, matching `hp:orgSz`/`hp:curSz`/`hp:sz`, and source-vs-HWP-exported-PDF page bounds/pixel difference; image presence alone is insufficient.
- Native GUI gate: run `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\capture_gui_states.ps1 -OutputDir .\.omo\evidence\task-7-pdf-fidelity-dnd\screenshots`. The script launches `tests\gui_state_harness.py` at 760×620, 800×680, and 1200×900 and captures default, valid-drop, invalid-drop, busy, success, warning, and error PNGs through Windows `System.Drawing.CopyFromScreen`. It exits nonzero if any named file is absent or blank. Tkinter is not a browser, so Lighthouse does not apply.

## Execution strategy
### Parallel execution waves
> Target 5-8 todos per wave. Fewer than 3 (except the final) means you under-split.

#### Wave 1 — contracts first (parallel)

- Todo 1: IBM design system and UI state/token contract.
- Todo 2: shared file intake contract for picker and file-list drops.
- Todo 3: PDF mode, layout asset, and diagnostic contract.

#### Wave 2 — integrate production paths

- Todo 4: dependency approval/install, runtime capabilities, and stack contract.
- Todo 5: mode-aware PDF parser, rendering, and diagnostics.
- Todo 6: HWP COM image-page writer and layout-safe finalization.
- Todo 7: IBM UI redesign, file-list drop interaction, and conversion locking.
- Todo 8: PyInstaller, README, and release-surface integration.

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| 1 | — | 7 | 2, 3 |
| 2 | — | 7 | 1, 3 |
| 3 | — | 5, 6 | 1, 2, 4 |
| 4 | — | 5, 7, 8 | 1, 2, 3 |
| 5 | 3, 4 | 6, 8 | 7 |
| 6 | 3, 5 | 8 | 7 |
| 7 | 1, 2, 4 | 8 | 5, 6 |
| 8 | 4, 5, 6, 7 | Final verification | — |

## Todos
> Implementation + Test = ONE todo. Never separate.
<!-- APPEND TASK BATCHES BELOW THIS LINE WITH edit/apply_patch - never rewrite the headers above. -->
- [x] 1. IBM Carbon 기반 디자인 시스템과 상태별 색 사용 계약을 고정한다.
  What to do / Must NOT do: `DESIGN.md`와 `ui_design.py`를 추가한다. 평면 사각형, 1px hairline, 4px grid, IBM Plex Sans/맑은 고딕 fallback을 기록하고 `ACTION_BLUE=#0F62FE`, `SUCCESS_GREEN=#24A148`, `WARNING_YELLOW=#F1C21B`, `ERROR_RED=#DA1E28`을 정의한다. `UI_STATE_COLORS`는 action/focus/info/drop-valid=Blue, success=Green, warning/drop-partial=Yellow, error/drop-rejected=Red로만 매핑한다. Green/Yellow/Red를 장식이나 일반 버튼에 사용하지 않고 IBM 로고·pill·shadow를 추가하지 않는다.
  Parallelization: Wave 1 | Blocked by: — | Blocks: 7
  References (executor has NO interview context - be exhaustive): `C:\Users\홍주형\OneDrive - 인천광역시교육청\바탕 화면\디자인 md\DESIGN-ibm.md`; `anyway_to_hwpx_gui.py:27-115`; `gui_preview.png`; frontend design-system gate.
  Acceptance criteria (agent-executable): `tests/test_ui_design_contract.py`가 네 색상 값, font fallback, 0px/2px geometry와 전체 상태 매핑을 검증한다. 역매핑 검사는 Green/Yellow/Red가 각각 success/warning/error 계열에만, Blue가 action/focus/info/drop-valid 계열에만 사용됨을 보장한다. `rg -n "#[0-9A-Fa-f]{6}" anyway_to_hwpx_gui.py` 결과가 비어 있다.
  QA scenarios (name the exact tool + invocation): Happy — `python -m unittest discover -s tests -p "test_ui_design_contract.py"`; Failure — IBM Plex가 없는 font-family mock과 semantic-color 오용 fixture가 각각 fallback 성공/테스트 실패를 증명한다. Evidence `.omo/evidence/task-1-pdf-fidelity-dnd.md`.
  Commit: Y | `docs(ui): establish IBM Carbon design contract`

- [x] 2. 파일 선택과 드롭이 공유하는 순수 입력 정규화 계층을 TDD로 만든다.
  What to do / Must NOT do: `gui_file_intake.py`에 `normalize_input_paths()`/`add_input_paths()`를 만들고 picker의 기존 dedupe/output-dir 로직을 이전한다. 실재 일반 파일, effective supported extensions, canonical path, 기존 선택, busy 여부를 판정해 accepted/duplicate/rejected/busy를 반환한다. TkDND raw data는 반드시 `self.tk.splitlist(event.data)`로만 해석하고 디렉터리나 공백 split을 허용하지 않는다.
  Parallelization: Wave 1 | Blocked by: — | Blocks: 7
  References (executor has NO interview context - be exhaustive): `anyway_to_hwpx_com.py:65-72`; `anyway_to_hwpx_gui.py:54-67`; `anyway_to_hwpx_gui.py:141-173`; `anyway_to_hwpx_gui.py:249-278`; tkinterdnd2 0.6.2 PyPI usage contract.
  Acceptance criteria (agent-executable): `tests/test_gui_file_intake.py`가 다중 파일 순서, brace/space 경로, canonical duplicate, missing/directory/unsupported, busy zero-accept, 최초 파일 output-dir default를 검증한다.
  QA scenarios (name the exact tool + invocation): Happy — `python -m unittest discover -s tests -p "test_gui_file_intake.py"`; Failure — busy와 mixed-validity 입력에서 호출자 목록이 변하지 않음을 검증한다. Evidence `.omo/evidence/task-2-pdf-fidelity-dnd.md`.
  Commit: Y | `test(gui): define shared file intake contract`

- [x] 3. PDF mode와 caller-owned 렌더링 자산 계약을 TDD로 정의한다.
  What to do / Must NOT do: `pdf_layout.py`와 `tests/test_pdf_layout_mode.py`를 추가한다. `layout`/`editable`, 200 DPI RGB PNG, uniform page size/orientation, 500 MiB cap, page-image block schema를 정의한다. Renderer는 임시 폴더를 만들거나 삭제하지 않고 반드시 caller가 전달한 `asset_dir` 안에만 쓴다. Pillow·OCR·text overlay·영구 raster cache는 금지한다.
  Parallelization: Wave 1 | Blocked by: — | Blocks: 5, 6
  References (executor has NO interview context - be exhaustive): `anyway_to_hwpx_com.py:1120-1149`; `anyway_to_hwpx_com.py:1300-1423`; `anyway_to_hwpx_com.py:1596-1618`; PyMuPDF `Page.get_pixmap()` official docs.
  Acceptance criteria (agent-executable): 생성형 A4 2쪽 fixture가 200 DPI PNG 2개와 point dimensions를 반환한다. Mixed orientation/size와 cap overflow는 actionable error다. 테스트는 caller directory가 scope 안에서는 유지되고 caller cleanup 뒤에만 제거됨을 검증한다.
  QA scenarios (name the exact tool + invocation): Happy — `python -m unittest discover -s tests -p "test_pdf_layout_mode.py"`; Failure — mixed-page, missing/unwritable asset-dir, cap-overflow 후 renderer가 외부 경로를 만들지 않음을 검증한다. Evidence `.omo/evidence/task-3-pdf-fidelity-dnd.md`.
  Commit: Y | `test(pdf): define fidelity asset contracts`

- [x] 4. 의존성 승인·설치와 runtime capability/stack 계약을 생산 코드보다 먼저 확정한다.
  What to do / Must NOT do: 실행 시작 시 설치 승인을 한 번 받고 `requirements.txt`에 `tkinterdnd2==0.6.2`, `opendataloader-pdf==2.4.7`을 추가한 뒤 `python -m pip install -r requirements.txt`를 실행한다. `runtime_capabilities.py`는 `find_spec()`과 Java probe 결과로 full/text/none capability를 만든다: full=layout+ODL editable, text=layout+pdfplumber/PyMuPDF/pypdf editable, none=PDF disabled. GUI fallback은 DnD unavailable이어도 picker를 유지한다. 자동 Java 설치와 version range 추측은 금지한다.
  Parallelization: Wave 2 | Blocked by: — | Blocks: 5, 7, 8
  References (executor has NO interview context - be exhaustive): `requirements.txt:1-8`; `anyway_to_hwpx_gui.spec:4-16`; PyPI `tkinterdnd2 0.6.2`; PyPI `opendataloader-pdf 2.4.7` (Python 3.10+, Java 11+).
  Acceptance criteria (agent-executable): `tests/test_runtime_capabilities.py`가 mocked module matrices에서 full/text/none을 정확히 판정하고, text가 layout을 지원하며 none에서 `.pdf`가 effective GUI input formats에서 빠짐을 검증한다. 설치 후 두 Python imports가 성공하고 Java 미설치는 ODL만 비활성화한다.
  QA scenarios (name the exact tool + invocation): Happy — `python -m unittest discover -s tests -p "test_runtime_capabilities.py"`; Failure — module-none과 Java<11 mock에서 앱은 import되고 PDF/ODL만 명시적으로 disabled 된다. Evidence `.omo/evidence/task-4-pdf-fidelity-dnd.md`.
  Commit: Y | `build(runtime): define PDF and DnD capabilities`

- [x] 5. `convert_file()`이 렌더 자산 수명과 PDF mode를 소유하도록 파서를 연결한다.
  What to do / Must NOT do: `--pdf-mode {layout,editable}` 기본 `layout`을 CLI→`convert_file()`→`detect_and_parse()`→`parse_pdf()`로 명시 전달한다. PDF layout일 때만 `convert_file()`이 `TemporaryDirectory`를 열고 `asset_dir`을 renderer에 전달하며, 해당 context는 `insert_pdf_page_image()`와 `SaveAs`가 끝날 때까지 유지된다. Editable은 현 ODL→pdfplumber→KORDOC→text 순서를 유지한다. Java probe는 5초 timeout note이며 fallback을 막지 않는다. 전역 mode/asset path와 silent fallback은 금지한다.
  Parallelization: Wave 2 | Blocked by: 3, 4 | Blocks: 6, 8
  References (executor has NO interview context - be exhaustive): `anyway_to_hwpx_com.py:96-117`; `anyway_to_hwpx_com.py:1120-1423`; `anyway_to_hwpx_com.py:1596-1618`; `anyway_to_hwpx_com.py:2675-2739`; `anyway_to_hwpx_com.py:2742-2825`.
  Acceptance criteria (agent-executable): `tests/test_pdf_mode_wiring.py`가 layout extraction bypass, editable fallback order, unavailable Java note를 검증한다. `insert_pdf_page_image()`와 `SaveAs` fake 모두에서 모든 image path가 존재하며, 성공·build failure·SaveAs failure 후에는 root temp dir가 제거됨을 검증한다.
  QA scenarios (name the exact tool + invocation): Happy — `python -m unittest discover -s tests -p "test_pdf_mode_wiring.py"`; Failure — invalid mode argparse, build/SaveAs injected failure에서 contextual error와 cleanup을 검증한다. Evidence `.omo/evidence/task-5-pdf-fidelity-dnd.md`.
  Commit: Y | `feat(pdf): add layout-first conversion mode`

- [x] 6. 검증된 HWP COM 계약으로 page image를 삽입하고 여섯 후처리를 분리한다.
  What to do / Must NOT do: 생산 helper 전에 gated COM contract test를 만든다. Page setup은 `CreateAction("PageSetup")`→`CreateSet()`→`GetDefault()`→`set.Item("PageDef")`에서 `PaperWidth=min(points)*100`, `PaperHeight=max(points)*100`, `Landscape=1 iff source width>height`, `TopMargin/BottomMargin/LeftMargin/RightMargin/HeaderLen/FooterLen/GutterLen=0`을 `SetItem`하고 `Execute(set)`한다. 그림은 `hwp.InsertPicture(path, True, 1, False, False, 0, width_points*25.4/72, height_points*25.4/72)`로 삽입하며 `sizeoption=1`의 mm contract를 사용한다. 페이지 사이에서만 `hwp.HAction.Run("BreakPage")`한다. False/exception이면 file conversion을 실패시키고 editable로 자동 fallback하지 않는다. Layout은 `apply_official_page_margins`, `apply_table_layout_profiles`, `apply_list_hanging_indents`, `fix_body_text_prid`, `apply_official_line_spacing`, `apply_official_paragraph_spacing` 여섯 개를 모두 건너뛰며 editable은 모두 유지한다. Editable 서식은 줄간격 160%, 문단 아래 간격 2, 장평·자간 기본값을 적용하고, 한국어 명사와 연결 조사가 줄바꿈에서 분리되지 않는지 검증한다. Direct HWPX image XML write는 금지한다.
  Parallelization: Wave 2 | Blocked by: 3, 5 | Blocks: 8
  References (executor has NO interview context - be exhaustive): `anyway_to_hwpx_com.py:1709-1716`; `anyway_to_hwpx_com.py:2234-2400`; `anyway_to_hwpx_com.py:2675-2739`; Hancom Automation `InsertPicture(path, embedded, sizeoption, reverse, watermark, effect, width, height)` official forum; Hancom `PageSetup` PageDef items; Hancom `BreakPage`; HWPUNIT=1/100 point; HWPX image schema `hp:orgSz`, `hp:curSz`, `hp:sz`.
  Acceptance criteria (agent-executable): fake COM test는 위 method/action/item 이름과 argument를 정확히 assert한다. `HWPX_RUN_COM_TESTS=1` test는 generated PDF→HWPX→HWP COM PDF round-trip을 수행하고 page count, pagePr dimensions/margins, pic count/sizes, source-vs-roundtrip non-white bounds ±2px 및 normalized mean absolute pixel error ≤0.05를 assert한다. Layout에서 여섯 postprocessor가 모두 uncalled, editable에서 모두 called다.
  QA scenarios (name the exact tool + invocation): Happy — `python -m unittest discover -s tests -p "test_pdf_hwp_image_writer.py"`; then `$env:HWPX_RUN_COM_TESTS='1'; python -m unittest discover -s tests -p "test_pdf_hwp_com_integration.py"`. Failure — PageSetup/InsertPicture/BreakPage 각각의 False/exception과 mixed page size가 HWPX를 남기지 않고 temp cleanup됨을 검증한다. Evidence `.omo/evidence/task-6-pdf-fidelity-dnd.md`.
  Commit: Y | `feat(hwp): preserve PDF page geometry`

- [x] 7. IBM UI, list-area DnD, 중앙 busy lock과 worker snapshot을 연결한다.
  What to do / Must NOT do: module import 단계에서 guarded `BaseTk = TkinterDnD.Tk` 또는 `tk.Tk`를 확정한 뒤 `ConverterApp(BaseTk)`를 정의한다. `list_wrap`과 `file_list`에만 DnD를 등록한다. `_set_busy(bool)` 하나가 add/remove/clear, output browse/entry, checkboxes, PDF mode, convert button을 모두 제어한다. `start_conversion()`은 files tuple, output_dir string, empty/mark/pdf mode bool/string snapshot을 worker args로 전달하고 worker는 live Tk variables를 읽지 않는다. 네 semantic colors는 Todo 1 상태에서만 사용한다.
  Parallelization: Wave 2 | Blocked by: 1, 2, 4 | Blocks: 8
  References (executor has NO interview context - be exhaustive): `anyway_to_hwpx_gui.py:1-67`; `anyway_to_hwpx_gui.py:124-246`; `anyway_to_hwpx_gui.py:249-416`; `DESIGN.md`; `gui_file_intake.py`; tkinterdnd2 0.6.2 `TkinterDnD.Tk`, `DND_FILES`, `splitlist`.
  Acceptance criteria (agent-executable): `tests/test_gui_drop_wiring.py`가 with/without DnD import, exact two drop target widgets, spaced Tcl list, PDF mode forwarding, 모든 mutable controls의 busy state, immutable worker snapshots을 검증한다. `scripts/capture_gui_states.ps1`가 21개(7 states×3 sizes) nonblank PNG를 생성하며 Blue/Green/Yellow/Red 대표 pixel/label mapping을 manifest로 검증한다.
  QA scenarios (name the exact tool + invocation): Happy — `python -m unittest discover -s tests -p "test_gui_drop_wiring.py"`; then `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\capture_gui_states.ps1 -OutputDir .\.omo\evidence\task-7-pdf-fidelity-dnd\screenshots`. Failure — no-DnD fallback, invalid drop, busy mutation attempts이 app crash/목록 변경 없이 안내 상태를 남긴다. Evidence `.omo/evidence/task-7-pdf-fidelity-dnd.md`.
  Commit: Y | `feat(gui): add IBM file-drop workflow`

- [x] 8. PyInstaller stack matrix, 설명서, 배포 smoke test를 정확한 PowerShell 명령으로 마감한다.
  What to do / Must NOT do: spec에 tkinterdnd2 binaries/data/hiddenimports를 수집하고 Pillow 없이 PyMuPDF pixmap 저장을 유지한다. README 양 언어에 mode tradeoff, scan behavior, Java, DnD fallback, full/text/none matrix를 동일하게 문서화한다. 모든 build는 workspace `dist/`/`build/`를 건드리지 않고 `C:\tmp\hwpx-gui-<stack>`에 쓴다. Full/text는 layout을 켜고 text는 ODL만 제외하며 none은 PDF picker/filter/drop/selector를 비활성화한다.
  Parallelization: Wave 2 | Blocked by: 4, 5, 6, 7 | Blocks: Final verification
  References (executor has NO interview context - be exhaustive): `anyway_to_hwpx_gui.spec:1-76`; `README.ko.md`; `README.md`; `verification-log.md:115`; runtime capability matrix from Todo 4.
  Acceptance criteria (agent-executable): 세 build가 import traceback 없이 시작한다. Full/text packaged apps both expose layout; full exposes ODL editable; text reports ODL absent but editable fallback available; none rejects PDF before conversion. DnD native runtime files exist in full/text/none packages. Korean/English docs match the same matrix.
  QA scenarios (name the exact tool + invocation): Happy — run exact PowerShell commands for each stack: `$env:HWPX_GUI_PDF_STACK='full'; python -m PyInstaller --clean --noconfirm --distpath 'C:\tmp\hwpx-gui-full\dist' --workpath 'C:\tmp\hwpx-gui-full\build' .\anyway_to_hwpx_gui.spec`; repeat with `text`/`none` and their paths. Failure — launch none build and drop a PDF; assert an actionable unsupported-format message and zero worker start. Evidence `.omo/evidence/task-8-pdf-fidelity-dnd.md`.
  Commit: Y | `build(release): package PDF fidelity and DnD matrix`

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.
- [ ] F1. Plan compliance audit — verify every Must have/NOT have and all eight todo receipts. Explicitly confirm full/text/none capability matrix, list-area-only DnD, semantic four-color mapping, caller-owned temp lifetime, and that layout skips exactly these six functions: `apply_official_page_margins`, `apply_table_layout_profiles`, `apply_list_hanging_indents`, `fix_body_text_prid`, `apply_official_line_spacing`, `apply_official_paragraph_spacing`. Record `.omo/evidence/f1-pdf-fidelity-dnd.md`.
- [ ] F2. Code quality review — run `python -m unittest discover -s tests`, `python -m py_compile anyway_to_hwpx_com.py anyway_to_hwpx_gui.py pdf_layout.py runtime_capabilities.py gui_file_intake.py ui_design.py`, and inspect temp ownership, contextual errors, COM return handling, duplicate constants, live Tk reads from worker, and raw semantic colors. Record `.omo/evidence/f2-pdf-fidelity-dnd.md`.
- [ ] F3. Real surface QA — run HWP COM preflight, gated PDF→HWPX→PDF geometry/pixel round-trip test, all three packaged stack smoke tests, and the exact PowerShell GUI-state capture script. Completion requires the round-trip geometry assertions and 21 nonblank state screenshots; self-report or image presence alone fails. Record `.omo/evidence/f3-pdf-fidelity-dnd.md`.
- [ ] F4. Scope fidelity — compare final `git status --short` to the captured preflight. Reject changes to protected dirty paths `dist/Anyway_to_hwpx(2026. 6. 11.).zip`, `gui_preview.png`, `samples/sample_complex.md`, direct HWPX image XML writes, cloud OCR, non-list drop targets, or `git add -A`. Run `git diff --check` and outbound-network-code search. Record `.omo/evidence/f4-pdf-fidelity-dnd.md`.

## Commit strategy
- Before edits, require `git rev-parse --show-toplevel` to resolve to this repository and save `git status --short` as the protected baseline. If not a Git repository, stop; do not silently switch to a copied/no-commit workspace.
- Commit after each completed todo using the exact message specified in that todo; stage only the paths named by that todo. Never use `git add -A` or combine unrelated user worktree changes.
- Before every commit, run the todo's unit command and `git diff --check`. Preserve `dist/Anyway_to_hwpx(2026. 6. 11.).zip`, `gui_preview.png`, `samples/sample_complex.md`, and planning/evidence artifacts unless separately authorized.
- A release build is evidence, not a commit trigger; include no `dist/`, `build/`, `out/`, temporary rendered PNG, or `.omo/evidence/` artifacts in commits unless repository policy is later changed.

## Success criteria
- A normal text or scanned PDF defaults to a visually faithful image-page HWPX; `editable` deliberately retains the older text/table reconstruction behavior.
- `editable` 출력은 줄간격 160%, 문단 아래 간격 2, 장평·자간 기본값을 사용하며 한국어 명사·연결 조사 단위가 잘리지 않는다. `layout` 출력은 원본 페이지 이미지의 서식을 변경하지 않는다.
- Each layout PDF page is inserted by HWP COM at its source physical dimensions; unsupported mixed page dimensions fail before document creation with an actionable mode suggestion.
- Files dropped onto the empty file-list area or list itself follow the same accepted/duplicate/rejected path as the file picker, including paths with spaces and multiple files.
- The redesigned native app uses IBM’s flat Carbon grammar and the four explicit functional chromatic colors with visible, accessible state changes.
- Full and text builds both support layout mode; only full bundles ODL, and none disables all PDF intake before worker start.
- Automated tests, COM integration, packaged executable startup, and native GUI visual evidence all pass; no direct HWPX image XML manipulation, cloud OCR, or unintended worktree changes are present.
