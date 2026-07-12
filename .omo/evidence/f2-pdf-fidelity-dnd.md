# F2 code-quality audit evidence

## Verdict

**NEEDS-FIX / needs-human-review.** The automated gates pass twice, and the GUI/Tk, temporary asset, and semantic-color inspections are clean. A concrete COM lifecycle gap remains in `convert_file()`: a build-stage exception can leave the current HWP document open because `doc.Close` is only registered in the later `SaveAs` `finally` block. Editable-path COM calls also do not consistently check false return values.

## Verification commands and exact results

Commands were run from `C:\Users\홍주형\.claude\hwpx-converter-renewal`.

1. `python -m unittest discover -s tests`

   ```text
   ----------------------------------------------------------------------
   Ran 215 tests in 29.590s

   OK (skipped=1)
   ```

2. `python -m unittest discover -s tests` (repeat)

   ```text
   ----------------------------------------------------------------------
   Ran 215 tests in 26.693s

   OK (skipped=1)
   ```

   Both passes exited 0. The expected runtime note reports Java 8 and the documented PDF editable fallback; it is not a test failure.

3. `python -m py_compile` over all 19 changed Python modules:

   ```text
   py_compile PASS: 19 modules
   ```

   Modules: `anyway_to_hwpx_com.py`, `anyway_to_hwpx_gui.py`, `gui_conversion_worker.py`, `gui_file_intake.py`, `gui_input_status.py`, `gui_layout.py`, `gui_theme.py`, `pdf_layout.py`, `runtime_capabilities.py`, `ui_design.py`, `tests/gui_state_harness.py`, `tests/test_gui_drop_wiring.py`, `tests/test_gui_file_intake.py`, `tests/test_pdf_hwp_com_integration.py`, `tests/test_pdf_hwp_image_writer.py`, `tests/test_pdf_layout_mode.py`, `tests/test_pdf_mode_wiring.py`, `tests/test_runtime_capabilities.py`, and `tests/test_ui_design_contract.py`.

4. `git diff --check`

   ```text
   git diff --check PASS
   ```

   Git emitted normal LF/CRLF conversion warnings only; no whitespace errors were reported.

## Pure LOC measurement

Method: physical line count, nonblank count, and noncomment count (`strip()` nonempty and not beginning with `#`) over the GUI modules and their split-out GUI support modules.

| module | physical | nonblank | pure noncomment |
| --- | ---: | ---: | ---: |
| `anyway_to_hwpx_gui.py` | 272 | 238 | 237 |
| `gui_conversion_worker.py` | 80 | 71 | 71 |
| `gui_file_intake.py` | 181 | 143 | 143 |
| `gui_input_status.py` | 54 | 48 | 48 |
| `gui_layout.py` | 237 | 229 | 229 |
| `gui_theme.py` | 37 | 33 | 33 |
| `ui_design.py` | 31 | 29 | 29 |
| **total** | **892** | **791** | **790** |

## Static inspection results

### Temporary asset ownership: PASS

- `pdf_layout.render_pdf_layout()` validates that the caller supplied an existing writable `asset_dir`; it does not create or remove the directory (`pdf_layout.py:93-129`).
- `convert_file()` owns a `TemporaryDirectory` for PDF layout conversion and keeps it around through rendering, COM insertion, and `SaveAs` (`anyway_to_hwpx_com.py:2868-2884`).
- On normal success, build failure, and `SaveAs` failure, the temporary root is released by the context manager. The repeated suite includes the asset-lifetime and failure-cleanup tests.

### GUI worker snapshot / live Tk reads: PASS

- `start_conversion()` captures a tuple of files plus primitive output/options/PDF-mode values before starting the thread (`anyway_to_hwpx_gui.py:204-218`).
- `_convert_worker()` constructs the frozen `ConversionSnapshot` from those arguments and calls `run_conversion`; it does not access `StringVar`/`BooleanVar` instances (`anyway_to_hwpx_gui.py:220-228`, `gui_conversion_worker.py:23-79`).
- Busy locking covers add/remove/clear, output browse and entry, both checkboxes, both PDF mode radios, and the convert button (`anyway_to_hwpx_gui.py:96-112`). DnD and list mutation handlers independently reject busy changes.

### COM return handling: PARTIAL / remaining risk

- The new layout path checks `PageSetup`, `InsertPicture`, `BreakPage`, `ParagraphShape`, and `SaveAs` results with `_require_hwp_success` (`anyway_to_hwpx_com.py:1776-1779`, `2350-2409`, `2840-2846`).
- **Remaining gap (P1):** `convert_file()` obtains `doc` at `anyway_to_hwpx_com.py:2823-2825`, but `doc.Close(isDirty=False)` is only in the `finally` attached to the subsequent `SaveAs` block (`2849-2853`). An exception in `build_doc()` / `insert_pdf_page_images()` (`2830-2837`) exits before that `finally`, so a failed item can leave an HWP document open while the worker continues with the same HWP process.
- **Remaining gap (P2):** editable-path `insert_text()` (`1746-1749`), `break_para()` (`1752-1753`), `set_char_shape()` (`1762-1773`), and table `TableCreate`/`TableColWidth` actions (`2296-2323`) ignore false COM return values. They catch exceptions in some places, but a COM `False` result can proceed silently.

### Contextual errors: PASS

- Layout build and save failures are wrapped with source filename and stage context (`anyway_to_hwpx_com.py:2834-2847`). PDF mode, mixed geometry, missing asset directory, and rendered-size-limit errors provide actionable messages through `pdf_layout.py`.

### Semantic colors / duplicate constants: PASS

- No six-digit color literals occur in the GUI modules outside the canonical `ui_design.py` token definitions. `gui_theme.py` aliases `ui_design.UI_STATE_COLORS`; it does not duplicate the hex values.
- `ui_design.py` is the single source for `#0F62FE`, `#24A148`, `#F1C21B`, and `#DA1E28`; state mappings are immutable via `MappingProxyType` and the contract tests passed.
- Other six-digit literals found by the repository-wide scan belong to table-document styling/tests, not GUI semantic state colors.

## Required follow-up

Move document closing into a `try/finally` that covers both build and save stages (and check its return if the COM API exposes one). Extend `_require_hwp_success` to the editable `insert_text`, `break_para`, `set_char_shape`, and table action execution paths, or document why those calls are intentionally exempt. Re-run both full unittest passes, the 19-module compile gate, and `git diff --check` after the fix.

## Post-audit update

The P1 `doc.Close` lifecycle gap was fixed after this audit.

Evidence: `.omo/evidence/fix-doc-close-on-build-failure.md`.

Post-fix verification:

```text
python -m unittest discover -s tests -p "test_pdf_mode_wiring.py"
Ran 13 tests in 3.160s
OK
```

```text
python -m unittest discover -s tests
Ran 216 tests in 22.203s
OK (skipped=1)
```

```text
python -m py_compile anyway_to_hwpx_com.py anyway_to_hwpx_gui.py pdf_layout.py runtime_capabilities.py gui_file_intake.py ui_design.py gui_conversion_worker.py gui_layout.py gui_theme.py gui_input_status.py
PASS
```

```text
git diff --check
PASS with LF/CRLF warnings only.
```

Remaining F2 risk after this update: editable-path COM return values are still not fully checked, and native F3 gates remain unconfirmed.

### Editable COM follow-up

The recorded unchecked-return risk is now reduced for `InsertText`, `BreakPara`, `CharShape`, and `TableCreate`. Each path has a red/green regression test; the full suite now reports 220 tests OK with one native COM skip. See `.omo/evidence/fix-editable-com-failure-detection.md`.

## Current regression refresh

After the packaging dependency setup and evidence reconciliation, `python -m unittest discover -s tests` reports **222 tests OK, 1 gated native COM skip**. The changed-module `py_compile` gate and `git diff --check` also pass.
