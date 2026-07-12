# Gate review — pdf-fidelity-dnd

## recommendation

REJECT

## originalIntent

사용자가 기대한 결과는 HWPX 변환기 갱신 구현 완료이다. 구체적으로 PDF는 기본값이 원본 페이지 모양을 보존하는 `layout` 모드이고, 필요 시 `editable` 모드를 선택할 수 있어야 한다. GUI는 파일 목록 영역에만 드롭을 허용하고, IBM Carbon 계열의 4개 의미 색상으로 상태를 보여야 한다. 변환 중 입력은 잠겨야 하고 worker는 불변 snapshot만 읽어야 한다. `editable` 출력은 줄간격 160%, 문단 아래 2, 기본 장평·자간, 한국어 명사+조사 어절 보호를 적용해야 하며 `layout` 출력에는 이 편집 서식 후처리가 적용되면 안 된다. 최종 완료는 단위 테스트뿐 아니라 HWP COM 왕복, 패키지 smoke, native GUI 시각 증거까지 통과해야 한다.

## desiredOutcome

사용자는 실제 Windows 환경에서 동작이 검증된 변환기를 받아야 한다.

- PDF layout 변환이 HWP COM으로 실제 페이지 크기·여백·그림 크기를 보존한다.
- PDF editable 변환은 기존 구조 변환 경로와 새 편집 기본 서식을 유지한다.
- GUI DnD는 list container와 Listbox에만 작동하고 busy 상태에서 입력 변경을 막는다.
- 7개 GUI 상태 × 3개 크기 = 21개 native screenshot이 실제 의미 색상과 responsive 상태를 입증한다.
- full/text/none PyInstaller 산출물이 각각 기대 capability matrix를 입증한다.
- final verification F1~F4가 모두 승인된다.

## userOutcomeReview

현재 산출물은 상당한 구현 진전이 있지만, 사용자에게 “완료된 결과물”로 넘길 수 없다. 전체 unittest 221개와 py_compile, diff check는 통과했지만, 최종 사용자 결과의 핵심인 HWP COM 실기 왕복과 패키지 빌드 smoke가 아직 증명되지 않았다. native GUI screenshot 21장은 현재 존재하지만, manifest의 요청 크기와 실제 PNG 크기가 일치하지 않고, `invalid-drop`/`warning` 상태의 의미 색상이 화면에 보이지 않아 시각 게이트를 통과시키기 어렵다.

## checkedArtifactPaths

- `.omo/plans/pdf-fidelity-dnd.md`
- `.omo/start-work/ledger.jsonl`
- `.omo/evidence/task-1-pdf-fidelity-dnd.md`
- `.omo/evidence/task-2-pdf-fidelity-dnd.md`
- `.omo/evidence/task-3-pdf-fidelity-dnd.md`
- `.omo/evidence/task-4-pdf-fidelity-dnd.md`
- `.omo/evidence/task-5-pdf-fidelity-dnd.md`
- `.omo/evidence/task-6-pdf-fidelity-dnd.md`
- `.omo/evidence/task-7-pdf-fidelity-dnd.md`
- `.omo/evidence/task-8-pdf-fidelity-dnd.md`
- `.omo/evidence/f1-pdf-fidelity-dnd.md`
- `.omo/evidence/f2-pdf-fidelity-dnd.md`
- `.omo/evidence/f3-pdf-fidelity-dnd.md`
- `.omo/evidence/f4-pdf-fidelity-dnd.md`
- `.omo/evidence/fix-doc-close-on-build-failure.md`
- `.omo/evidence/fix-editable-com-failure-detection.md`
- `.omo/evidence/task-7-pdf-fidelity-dnd/screenshots/manifest.json`
- all 21 PNG files under `.omo/evidence/task-7-pdf-fidelity-dnd/screenshots/`
- `native-qa.txt`
- `DESIGN.md`
- `README.md`
- `README.ko.md`
- `requirements.txt`
- `anyway_to_hwpx_gui.spec`
- `scripts/capture_gui_states.ps1`
- `scripts/packaging_smoke.ps1`
- `tests/gui_state_harness.py`
- `tests/test_gui_drop_wiring.py`
- `tests/test_pdf_hwp_com_integration.py`
- `tests/test_pdf_hwp_image_writer.py`
- `anyway_to_hwpx_gui.py`
- `gui_layout.py`
- `gui_theme.py`
- `gui_input_status.py`
- `gui_conversion_worker.py`
- `gui_file_intake.py`
- `ui_design.py`
- `pdf_layout.py`
- `runtime_capabilities.py`
- `anyway_to_hwpx_com.py`

## commandsRun

```text
python -m unittest discover -s tests
Ran 221 tests in 28.367s
OK (skipped=1)
```

```text
python -m py_compile anyway_to_hwpx_com.py anyway_to_hwpx_gui.py pdf_layout.py runtime_capabilities.py gui_file_intake.py ui_design.py gui_conversion_worker.py gui_layout.py gui_theme.py gui_input_status.py tests\gui_state_harness.py tests\test_gui_drop_wiring.py tests\test_gui_file_intake.py tests\test_pdf_hwp_com_integration.py tests\test_pdf_hwp_image_writer.py tests\test_pdf_layout_mode.py tests\test_pdf_mode_wiring.py tests\test_runtime_capabilities.py tests\test_ui_design_contract.py
exit 0
```

```text
git diff --check
exit 0; LF/CRLF warnings only
```

```text
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\packaging_smoke.ps1
[SKIP] full: missing Python package(s): tkinterdnd2
[SKIP] text: missing Python package(s): tkinterdnd2
[SKIP] none: missing Python package(s): tkinterdnd2
```

## visualQA

Verdict: FAIL.

Inspected count: 21/21 screenshots.

Files inspected:

- `default-760x620.png`, `valid-drop-760x620.png`, `invalid-drop-760x620.png`, `busy-760x620.png`, `success-760x620.png`, `warning-760x620.png`, `error-760x620.png`
- `default-800x680.png`, `valid-drop-800x680.png`, `invalid-drop-800x680.png`, `busy-800x680.png`, `success-800x680.png`, `warning-800x680.png`, `error-800x680.png`
- `default-1200x900.png`, `valid-drop-1200x900.png`, `invalid-drop-1200x900.png`, `busy-1200x900.png`, `success-1200x900.png`, `warning-1200x900.png`, `error-1200x900.png`

Findings:

- All 21 files exist and are nonzero-length.
- Manifest requested sizes do not match actual image pixel sizes:
  - `760x620` entries are actual `776x659`.
  - `800x680` entries are actual `816x719`.
  - `1200x900` entries are actual `1216x884`.
- `success` screenshots visibly show green log text.
- `error` screenshots visibly show red log text.
- `invalid-drop` screenshots do not visibly show a red rejected-drop state; they look like the default state with `파일을 선택하세요.`
- `warning` screenshots do not visibly show yellow warning state; harness writes the warning log with tag `"muted"`, and `gui_layout.py` defines only `ok`, `err`, and `muted` log tags.
- `valid-drop` state shows a file added, but the visible blue evidence is dominated by the primary action button rather than a distinct drop-valid state indicator.
- `scripts/capture_gui_states.ps1` writes manifest fields `width`/`height` from requested geometry, not from actual captured bitmap dimensions, so manifest does not prove exact output dimensions.
- `task-7` evidence claims unique SHA-256 hashes, but current `manifest.json` contains no hash fields.

Relevant code evidence:

- `tests/gui_state_harness.py` uses `_append_log("확인 필요: PDF 스캔 문서", "muted")` for warning.
- `gui_layout.py` configures `ok` as green, `err` as red, and `muted` as gray; it does not configure a warning/yellow log tag.
- `gui_theme.py` exposes `GREEN` and `RED` from semantic tokens but no `WARNING_YELLOW` alias used by the GUI.

## codeAndScopeReview

Confirmed:

- `anyway_to_hwpx_gui.py` registers DnD only on `self.list_wrap` and `self.file_list`.
- Drop handling uses `self.tk.splitlist(event.data)` before passing paths to the intake helper.
- `_set_busy()` disables add/remove/clear, output browse/entry, checkboxes, PDF radios, and convert button.
- `start_conversion()` snapshots `files`, `output_dir`, booleans, and `pdf_mode` before starting the worker.
- `gui_conversion_worker.py` receives `ConversionSnapshot` and does not read live Tk variables.
- `anyway_to_hwpx_com.py` layout path uses HWP COM `InsertPicture`, `PageSetup`, and `BreakPage`.
- Layout path skips the six editable postprocessors after save; editable path calls them.
- `InsertText`, `BreakPara`, `CharShape`, and `TableCreate` now check false COM returns through `_require_hwp_success`.
- Static search found no production cloud OCR/upload/network client code and no production direct HWPX image XML writer.

Unresolved:

- HWP COM integration test is still skipped unless `HWPX_RUN_COM_TESTS=1`; current unittest output has 1 skip.
- `f3-pdf-fidelity-dnd.md` still records HWP COM preflight timeout, no successful HWP COM round-trip, skipped packaging builds, and stale GUI capture failure.
- `native-qa.txt` is stale invalid evidence containing `ModuleNotFoundError: No module named 'anyway_to_hwpx_gui'`.
- Plan checkboxes still show Todo 7 and F1~F4 unchecked in `.omo/plans/pdf-fidelity-dnd.md`.
- `anyway_to_hwpx_com.py` is still 2,519 pure LOC. That is a programming/code-smell defect. It is legacy scope, but the final gate cannot treat the module as structurally clean.

## slopAndOverfitReview

Consulted criteria:

- `omo:programming`
- `omo:programming/references/python/README.md`
- `omo:programming/references/code-smells.md`
- `omo:remove-ai-slops`

Direct slop/overfit pass:

- No obvious screenshot-raster fake UI was found; screenshots show real Tk windows with native title bars and widgets.
- Test suite includes useful behavior coverage for DnD snapshotting, PDF mode wiring, COM fake failures, layout assets, runtime capability matrix, and design tokens.
- However, the visual-state tests/evidence are over-optimistic: manifest labels assert semantic states that are not visibly rendered for warning and invalid-drop.
- `tests/test_gui_drop_wiring.py` includes source-string characterization assertions. These can be useful as a seam guard, but they are weaker than behavior-level widget assertions and do not prove the native visual contract.
- Current final code-review coverage is incomplete: F2 is a code-quality audit, but no current approving code-review artifact explicitly applies both `remove-ai-slops` and `programming` overfit/slop criteria to the full final diff. F4 has a direct slop paragraph, but it is stale against newer screenshots and still rejects.
- Evidence claims drift exists: F1/F3/F4 report missing screenshots, while Task 7 later claims screenshots were regenerated. The final verification artifacts were not rerun and approved after that new evidence.

## blockers

1. HWP COM surface proof is missing. The required `HWPX_RUN_COM_TESTS=1` PDF→HWPX→PDF geometry/pixel round-trip is not successful in current evidence, and current unittest still has the native COM integration skip.
2. Packaging proof is missing. `scripts/packaging_smoke.ps1` still skips full/text/none because `tkinterdnd2` is not installed, so packaged startup, runtime file collection, and none-stack PDF rejection are unproven.
3. Visual QA fails. All 21 screenshots were inspected, but actual PNG dimensions do not match manifest sizes; warning yellow and drop-rejected red are not visibly represented.
4. Evidence is internally inconsistent and stale. F3 still says native GUI capture failed, while Task 7 now says capture completed. F1/F3/F4 were not rerun to approval after the alleged fresh screenshots.
5. Plan completion is not reflected. Todo 7 and F1~F4 remain unchecked in `.omo/plans/pdf-fidelity-dnd.md`.
6. `native-qa.txt` remains stale invalid evidence.
7. No final approving code-review artifact explicitly covers the full diff with both `remove-ai-slops` and `programming` overfit/slop criteria.

## exactEvidenceGaps

- Missing successful `python anyway_to_hwpx_com.py --preflight` evidence.
- Missing successful `HWPX_RUN_COM_TESTS=1 python -m unittest discover -s tests -p "test_pdf_hwp_com_integration.py"` transcript.
- Missing HWP COM-exported PDF geometry/pixel comparison artifact.
- Missing successful full/text/none PyInstaller package build transcripts.
- Missing packaged app startup proof for full/text/none.
- Missing none-stack PDF intake rejection proof from a packaged executable.
- Missing native DnD runtime file proof from packaged full/text/none builds.
- Missing final F1/F2/F3/F4 rerun after fresh screenshot generation.
- Missing screenshot manifest hash fields despite evidence claiming unique SHA-256 hashes.
- Missing visual proof that `warning` uses `#F1C21B` and `drop-rejected` uses `#DA1E28`.
- Missing rendered/native proof that Korean noun+postposition wrapping is preserved; current proof is a fake-COM `BreakNonLatinWord=0` property assertion only.

## conclusion

The implementation is not gate-ready. The next fixes should update the GUI state rendering/harness so warning and drop rejection visibly use the required semantic colors, regenerate manifest using actual bitmap dimensions and hashes, rerun F1/F3/F4 after the fresh visual evidence, install or provide `tkinterdnd2` for real package smoke, and run the native HWP COM preflight/round-trip gate in an environment where HWP COM responds.
