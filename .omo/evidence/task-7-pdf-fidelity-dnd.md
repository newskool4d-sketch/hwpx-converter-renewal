# Todo 7 evidence

## Baseline and RED

- Preflight preserved the dirty baseline: deleted `dist/Anyway_to_hwpx(2026. 6. 11.).zip`, untracked `.omo/`, `gui_preview.png`, and `samples/sample_complex.md`; concurrent task files were not reverted.
- Initial command: `python -m unittest discover -s tests -p "test_gui_drop_wiring.py"`
- Initial result: 1 failure because `BaseTk` was absent; the characterization test therefore failed for the requested missing guarded import seam.

## Implemented behavior

- `BaseTk` is selected from `TkinterDnD.Tk` with an `ImportError` fallback to `tk.Tk`.
- Only `list_wrap` and `file_list` register `DND_FILES`; drop data is passed through `self.tk.splitlist(event.data)` before `gui_file_intake`.
- Picker and drop use `add_input_paths`; duplicates, missing paths, directories, and unsupported extensions are summarized with actionable status text; the first accepted file supplies a blank output folder.
- `_set_busy(bool)` locks list mutation, output browse/entry, both checkboxes, both PDF mode controls, and conversion start. Capability `none` keeps PDF controls disabled after unlock.
- Worker receives tuple-owned files, output folder, booleans, and an immutable PDF mode snapshot. The worker does not read Tk variables and forwards `pdf_mode` without changing layout mode.
- GUI colors use `ui_design` semantic tokens for action/focus/success/error and no six-digit GUI hex literals remain.

## Verification

- `python -m unittest discover -s tests -p "test_gui_drop_wiring.py"`: PASS, 4 tests.
- Repeated GUI unittest run: PASS.
- `python -m py_compile anyway_to_hwpx_gui.py tests/test_gui_drop_wiring.py tests/gui_state_harness.py`: PASS.
- `git diff --check`: PASS.
- `rg -n "#[0-9A-Fa-f]{6}" anyway_to_hwpx_gui.py`: no matches.

## Adversarial classes

- Missing dependency: guarded TkDND import falls back to standard Tk while picker remains available.
- Raw Tcl payload: direct event data never reaches the pure intake helper; only the caller-owned `splitlist` result is accepted.
- Stale mutable state: conversion starts from tuple/primitive snapshots; later UI changes cannot alter worker arguments.
- Busy mutation: drop, picker, clear, delete, output browse, entry, checkboxes, PDF controls, and conversion button are all guarded.
- Capability none: PDF filter/drop acceptance and mode controls are disabled while non-PDF conversion remains available.
- Misleading success: the new test asserts the captured `editable` mode remains `editable` after the UI variable changes to `layout`.

## Native capture

`scripts/capture_gui_states.ps1` and `tests/gui_state_harness.py` implement the required 7 states × 3 sizes (21 PNGs plus `manifest.json`).

Fresh native capture completed on 2026-07-11:

- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\capture_gui_states.ps1 -OutputDir .\.omo\evidence\task-7-pdf-fidelity-dnd\screenshots`
- Result: `Captured 21 screenshots`.
- The harness inserts the repository root before importing the app, gives each Tk window a unique QA title, and the capture script selects the owned Tk window instead of the Python console.
- Captures use Windows `PrintWindow`, preventing unrelated always-on-top windows from contaminating the PNGs.
- Manifest reports seven states at each of 760×620, 800×680, and 1200×900; all 21 files are nonblank and have unique SHA-256 hashes.
- Direct inspection found the original minimum-width formatting notice clipped. The notice was shortened to `편집: 줄간격 160% · 아래 2 · 장평/자간 기본 · 어절 보호`, protected by a regression test, and all 21 screenshots were regenerated after that edit.
- Latest regression: `python -m unittest discover -s tests` → 221 tests OK, 1 skipped native HWP COM integration gate.

## Current evidence location

- Authoritative latest capture: `.omo/evidence/task-7-pdf-fidelity-dnd/screenshots-final/`
- `manifest.json` records 7 states × 3 sizes, 21 nonblank PNGs with unique hashes.
