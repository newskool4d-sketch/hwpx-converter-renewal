# F1 audit — PDF fidelity / DnD plan compliance

## Verdict

**NEEDS-HUMAN-REVIEW / NEEDS-FIX.** The source-level contracts and COM-free tests cover the requested wiring, and the latest native GUI capture is now present. F1 remains open only for the packaged full/text/none smoke builds, HWP COM round-trip evidence, and ledger reconciliation for Todo 7.

## Evidence inspected

- Plan: `.omo/plans/pdf-fidelity-dnd.md` (Must-have/NOT-have, Todo 1–8, F1 gate).
- Receipts: `.omo/evidence/task-1-pdf-fidelity-dnd.md` through `task-8-pdf-fidelity-dnd.md` (all eight files exist).
- Ledger: `.omo/start-work/ledger.jsonl` (completion events exist for 1–6 and 8; no event for 7).
- Current source/tests: `anyway_to_hwpx_com.py`, `pdf_layout.py`, `runtime_capabilities.py`, `anyway_to_hwpx_gui.py`, `gui_file_intake.py`, `gui_conversion_worker.py`, `ui_design.py`, and the relevant `tests/` files.

## Confirmed

1. **full/text/none capability contract.** `runtime_capabilities.py` uses `find_spec()` and Java probing. Full requires layout plus ODL/Java 11+, text retains layout plus local editable fallback, and none removes `.pdf` from effective input extensions and rejects PDF before parsing. `test_runtime_capabilities.py` passed 7/7; the current source and both README matrices agree.

2. **Layout-first wiring and caller-owned lifetime.** CLI default is `--pdf-mode layout`; the mode is passed explicitly through `convert_file()` → `detect_and_parse()` → `parse_pdf()`. Layout owns a `TemporaryDirectory` through image insertion and `SaveAs`; tests cover success/build-failure/save-failure cleanup. `test_pdf_mode_wiring.py` passed 12/12.

3. **Exactly six layout postprocessor bypasses.** The rendered-layout branch inserts page images and returns before these editable-only calls: `apply_official_page_margins`, `apply_table_layout_profiles`, `apply_list_hanging_indents`, `fix_body_text_prid`, `apply_official_line_spacing`, and `apply_official_paragraph_spacing`. The editable branch calls all six. Both source inspection and the layout negative-call tests confirm no additional postprocessor is used for layout. `test_pdf_hwp_image_writer.py` passed 12/12.

4. **Editable defaults.** `set_para_shape()` sends line spacing `160`, `NextSpacing=200` (the implementation’s 2-unit contract), and `BreakNonLatinWord=0`; `set_char_shape()` does not set character ratio or spacing, preserving HWP defaults. The current fake-COM test asserts these values and passes. Korean noun/postposition wrapping is represented by the non-Latin-break setting, but no rendered Korean HWP/COM assertion is present (see gaps).

5. **DnD scope and snapshots.** `anyway_to_hwpx_gui.py` registers DnD only on `list_wrap` and `file_list`, parses event data via `self.tk.splitlist(event.data)`, and shares `add_input_paths()` with the picker. `_set_busy()` locks list controls, output browse/entry, both checkboxes, both PDF radios, and conversion start. `start_conversion()` snapshots tuple/primitive values and the worker reads `ConversionSnapshot`, not live Tk variables. Current `test_gui_drop_wiring.py` passed 4/4 (the Todo 7 receipt says 3, so that receipt is stale).

6. **Guardrails.** No production `hp:pic`/`orgSz`/`curSz` image XML writer is present; layout images are inserted only through HWP COM `InsertPicture(...)`. Static search found no cloud OCR/upload/network client code. Existing XML postprocessors are editable-path functions and are not invoked for layout. No non-list DnD registrations were found.

7. **Protected baseline.** Current `git status --short` still shows the protected deleted distribution ZIP and untracked `gui_preview.png` / `samples/sample_complex.md`; no diff was found for the two untracked protected files. Existing receipts consistently report that those paths were preserved.

8. **COM-free regression status.** `python -m unittest discover -s tests` currently passes 215 tests with one intentional gated skip; the targeted GUI, mode-wiring, image-writer, and runtime suites also pass.

## Needs-fix / unproven gates

- **Native GUI gate:** latest evidence is present under `.omo/evidence/task-7-pdf-fidelity-dnd/screenshots-final/` with 21 nonblank PNGs and `manifest.json`. The older failed-capture transcript remains historical and must not be used as the current result.
- **Packaging gate missing:** Todo 8’s full/text/none PyInstaller builds were skipped because `tkinterdnd2` is not installed. No packaged executable startup, none-stack PDF rejection, or native DnD runtime-file evidence exists.
- **HWP COM fidelity gate missing:** `test_pdf_hwp_com_integration.py` is skipped unless `HWPX_RUN_COM_TESTS=1`; there is no verified page-count/pagePr/picture-size or source-vs-roundtrip pixel result. The required HWP preflight was not recorded in the Todo 6 receipt.
- **Receipt integrity:** `.omo/start-work/ledger.jsonl` lacks a Todo 7 completion record even though `task-7-pdf-fidelity-dnd.md` exists. The receipt’s reported 3 GUI tests disagrees with the current 4-test file.
- **Korean wrapping proof:** only the `BreakNonLatinWord=0` fake-COM property is asserted; the plan asks for a Korean noun+postposition non-splitting behavior check, and no rendered/native assertion is recorded.

## Reproduction commands run for this audit

```text
python -m unittest discover -s tests -p "test_gui_drop_wiring.py"       # 4 passed
python -m unittest discover -s tests -p "test_pdf_mode_wiring.py"      # 12 passed
python -m unittest discover -s tests -p "test_pdf_hwp_image_writer.py"  # 12 passed
python -m unittest discover -s tests -p "test_runtime_capabilities.py"  # 7 passed
python -m unittest discover -s tests                              # 215 passed, 1 gated skip
```
