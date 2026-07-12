# F4 Gate Review: pdf-fidelity-dnd

## recommendation

REJECT

## finalVerdict

needs-fix

## originalIntent

Deliver a renewed HWPX converter where PDF conversion defaults to visually faithful layout mode, editable PDF mode remains available, file-list drag-and-drop is supported through shared intake logic, the native GUI uses the IBM Carbon-style state design, and release/docs/package surfaces consistently expose the full/text/none PDF stack matrix.

## desiredOutcome

The user should receive a working Windows-native converter with authoritative automated evidence for unit behavior, HWP COM PDF geometry/pixel round-trip, packaged executable smoke checks, and 21 nonblank native GUI screenshots covering 7 states at 3 sizes.

## userOutcomeReview

The shipped artifact is not yet supported by the required evidence. The code may contain substantial implementation work, but the user-visible outcome cannot be confirmed because native GUI screenshots were not produced, HWP COM round-trip remained gated/skipped, package builds were skipped, final verification artifacts are missing, and stale code-review artifacts still contain unresolved blockers.

## checkedArtifactPaths

- `.omo/plans/pdf-fidelity-dnd.md`
- `.omo/start-work/ledger.jsonl`
- `.omo/evidence/task-1-pdf-fidelity-dnd.md`
- `.omo/evidence/task-1-pdf-fidelity-dnd-code-review.md`
- `.omo/evidence/task-2-pdf-fidelity-dnd.md`
- `.omo/evidence/task-2-pdf-fidelity-dnd-code-review.md`
- `.omo/evidence/task-3-pdf-fidelity-dnd.md`
- `.omo/evidence/task-3-pdf-fidelity-dnd-code-review.md`
- `.omo/evidence/task-4-pdf-fidelity-dnd.md`
- `.omo/evidence/task-5-pdf-fidelity-dnd.md`
- `.omo/evidence/task-6-pdf-fidelity-dnd.md`
- `.omo/evidence/task-7-pdf-fidelity-dnd.md`
- `.omo/evidence/task-8-pdf-fidelity-dnd.md`
- `native-qa.txt`
- `.omo/evidence/f3-pdf-fidelity-dnd/`
- `.omo/evidence/task-7-pdf-fidelity-dnd/`
- `README.md`, `README.ko.md`, `DESIGN.md`, `requirements.txt`, `anyway_to_hwpx_gui.spec`
- Current `git status --short`, `git diff --name-status`, `git diff --check`

## blockers

1. Todo 7 is still unchecked in the plan and lacks authoritative native GUI evidence. `.omo/evidence/task-7-pdf-fidelity-dnd.md` says the capture command was not run and must be run from an interactive Windows session. The required 21 PNGs plus manifest are absent.
2. `native-qa.txt` is stale/invalid evidence. It contains only `ModuleNotFoundError: No module named 'anyway_to_hwpx_gui'` from `tests/gui_state_harness.py`, not screenshots or a passing manifest.
3. Final Verification Wave is not complete. F1, F2, F3, and F4 are unchecked in the plan. No F1 or F2 evidence file exists, and `.omo/evidence/f3-pdf-fidelity-dnd/` is empty.
4. HWP COM surface proof is missing. Task 6 records `test_pdf_hwp_com_integration.py` as skipped because `HWPX_RUN_COM_TESTS` was unset, so the required page geometry/pixel round-trip was not proven.
5. Packaging proof is missing. Task 8 records full/text/none PyInstaller builds as skipped because `tkinterdnd2` was absent, so packaged startup and DnD runtime collection are not proven.
6. Code review coverage is missing/stale. Only Todo 1-3 code-review artifacts were found; Todo 2 and Todo 3 code-review artifacts still say `BLOCK` / `REQUEST_CHANGES`. There is no supported final code-quality review covering Todos 4-8 or the required remove-ai-slops/programming overfit/slop criteria.

## planCheckboxAudit

| Item | Plan checkbox | Evidence support |
| --- | --- | --- |
| Todo 1 design system | checked | Supported by task evidence and an approving code review. |
| Todo 2 shared intake | checked | Implementation evidence exists, but code-review artifact is stale and still blocking. Not cleanly supported. |
| Todo 3 PDF layout contract | checked | Unit evidence exists, but code-review artifact is stale and still blocking on evidence quality. Not cleanly supported. |
| Todo 4 runtime capabilities | checked | Focused unit evidence exists; no final review artifact. |
| Todo 5 PDF mode wiring | checked | Focused/full unit evidence exists; no final review artifact. |
| Todo 6 HWP image writer | checked | Fake COM/unit evidence exists; native COM round-trip skipped. Partially supported only. |
| Todo 7 GUI/DnD/native states | unchecked | Unit evidence exists; required native screenshots/manifest absent. Not supported. |
| Todo 8 packaging/docs | checked | Docs/spec checks exist; full/text/none builds skipped. Partially supported only. |
| F1 plan compliance audit | unchecked | Missing artifact. |
| F2 code quality review | unchecked | Missing artifact. |
| F3 real surface QA | unchecked | Empty artifact directory; required COM, packaging, and GUI screenshots missing. |
| F4 scope fidelity | unchecked before this file | This file records REJECT. |

## evidenceHygieneAudit

- `native-qa.txt` is invalid because it records an import failure, not a native QA run.
- `.omo/evidence/task-7-pdf-fidelity-dnd/` and `.omo/evidence/f3-pdf-fidelity-dnd/` contain no screenshot or manifest files.
- `.omo/evidence/task-2-pdf-fidelity-dnd-code-review.md` and `.omo/evidence/task-3-pdf-fidelity-dnd-code-review.md` remain stale blocking reports. Later evidence may claim fixes, but the review reports were not replaced with approving artifacts.
- Several evidence files rely on skipped gates: HWP COM integration skipped, PyInstaller builds skipped, native capture skipped.

## docsSpecCodeConsistencyAudit

- `README.md`, `README.ko.md`, `requirements.txt`, and `anyway_to_hwpx_gui.spec` are broadly aligned on `tkinterdnd2==0.6.2`, `opendataloader-pdf==2.4.7`, full/text/none stack semantics, Java 11+ ODL behavior, DnD fallback, layout/editable tradeoffs, and no cloud OCR.
- `DESIGN.md` and the GUI sources align on semantic color tokens; `rg` found no six-digit hex literals in `anyway_to_hwpx_gui.py`.
- Consistency is still not sufficient for approval because the documented package/native behavior has not been proven by the required executable builds or GUI screenshots.

## dirtyWorktreeAudit

Current `git status --short` includes:

```text
 M README.ko.md
 M README.md
 M anyway_to_hwpx_com.py
 M anyway_to_hwpx_gui.py
 M anyway_to_hwpx_gui.spec
 D "dist/Anyway_to_hwpx(2026. 6. 11.).zip"
 M requirements.txt
?? .omo/
?? DESIGN.md
?? gui_conversion_worker.py
?? gui_file_intake.py
?? gui_input_status.py
?? gui_layout.py
?? gui_preview.png
?? gui_theme.py
?? native-qa.txt
?? pdf_layout.py
?? runtime_capabilities.py
?? samples/sample_complex.md
?? scripts/
?? tests/gui_state_harness.py
?? tests/test_gui_drop_wiring.py
?? tests/test_gui_file_intake.py
?? tests/test_pdf_hwp_com_integration.py
?? tests/test_pdf_hwp_image_writer.py
?? tests/test_pdf_layout_mode.py
?? tests/test_pdf_mode_wiring.py
?? tests/test_runtime_capabilities.py
?? tests/test_ui_design_contract.py
?? ui_design.py
```

The protected dirty paths `dist/Anyway_to_hwpx(2026. 6. 11.).zip`, `gui_preview.png`, and `samples/sample_complex.md` are recorded by task evidence as pre-existing baseline entries. They still require careful preservation, but I did not find evidence in this audit that they were newly introduced by this wave. Task changes are the tracked source/docs/spec/requirements modifications plus new modules/tests/scripts/evidence.

`git diff --name-status` only reports tracked changes and therefore omits untracked task files. `git diff --check` produced only LF/CRLF conversion warnings and no whitespace-error output.

## directSlopOverfitPass

Applied the `remove-ai-slops` and `programming` review lenses directly over the available diff/evidence surface. Blocking issues are evidence/report slop rather than a confirmed production-code defect: skipped surface gates are being presented next to completed todos, stale blocking reviews were not resolved, and unit evidence is being used where the plan explicitly requires native COM/package/GUI artifacts. This creates false confidence and fails the requested overfit/slop gate.

## exactEvidenceGaps

- Missing: 21 nonblank GUI screenshots and `manifest.json`.
- Missing: successful native `scripts/capture_gui_states.ps1` transcript.
- Missing: successful `HWPX_RUN_COM_TESTS=1` PDF→HWPX→PDF geometry/pixel round-trip transcript.
- Missing: successful full/text/none packaged executable smoke transcripts.
- Missing: F1 and F2 final verification reports.
- Missing/stale: approving code-review report covering the final changed surface and explicit remove-ai-slops/programming criteria.

## conclusion

The work needs a fix/review loop before it can be confirmed. The decisive blockers are missing native surface evidence, skipped COM/package gates, unchecked final verification, and stale blocking review artifacts.

## Post-review update

After this F4 review, F1/F2/F3 evidence files were created:

- `.omo/evidence/f1-pdf-fidelity-dnd.md`
- `.omo/evidence/f2-pdf-fidelity-dnd.md`
- `.omo/evidence/f3-pdf-fidelity-dnd.md`

F2's P1 `doc.Close` lifecycle finding was fixed and recorded in `.omo/evidence/fix-doc-close-on-build-failure.md`. The current full unittest suite reports 216 tests passing with 1 gated COM skip.

This does not change the F4 verdict. The remaining decisive blockers are still native GUI screenshots, HWP COM preflight/round-trip, real packaged executable smoke tests, and the residual editable-path COM return-value review.
