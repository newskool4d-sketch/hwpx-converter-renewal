# Todo 5 — mode-aware PDF parser and asset lifetime

## Scope and protected baseline

Pre-flight repository:

```text
git rev-parse --show-toplevel
C:/Users/홍주형/.claude/hwpx-converter-renewal

git status --short
 D "dist/Anyway_to_hwpx(2026. 6. 11.).zip"
?? .omo/
?? gui_preview.png
?? samples/sample_complex.md
```

The protected deleted distribution ZIP and unrelated artifacts were preserved.
The shared worktree also contains other agents' GUI/runtime/layout changes; no
protected file was reverted.

## TDD receipt

Initial RED run before production wiring:

```text
python -m unittest discover -s tests -p "test_pdf_mode_wiring.py"
..FFEEE
======================================================================
ERROR: test_layout_parse_bypasses_text_extractors_and_receives_caller_asset_directory
...
AttributeError: <module 'anyway_to_hwpx_com' ...> does not have the attribute 'render_pdf_layout'
======================================================================
FAIL: test_cli_exposes_layout_as_the_default_pdf_mode
...
AssertionError: '--pdf-mode {layout,editable}' not found in "usage: ..."
======================================================================
FAIL: test_invalid_pdf_mode_is_rejected_without_global_state
...
AssertionError: 'layout' not found in "convert_file() got an unexpected keyword argument 'pdf_mode'"
----------------------------------------------------------------------
Ran 7 tests in 0.073s

FAILED (failures=2, errors=3)
```

This is the actual failure shape captured before production wiring: the CLI
option and conversion keyword were absent, and the public renderer seam was
missing from the converter module.

After wiring and adversarial tests:

```text
python -m unittest discover -s tests -p "test_pdf_mode_wiring.py"  # run 1
..........
Ran 10 tests in 0.894s
OK

python -m unittest discover -s tests -p "test_pdf_mode_wiring.py"  # run 2
..........
Ran 10 tests in 0.888s
OK
```

Relevant and full regression checks:

```text
python -m unittest discover -s tests -p "test_pdf_layout_mode.py"
.........
Ran 9 tests ...
OK

python -m unittest discover -s tests -p "test_runtime_capabilities.py"
.......
Ran 7 tests ...
OK

python -m unittest discover -s tests -p "test_conversion_diagnostics.py"
...
Ran 3 tests ...
OK

python -m unittest discover -s tests
Ran 199 tests in 19.922s
OK
```

The earlier `199` count is superseded by the post-GUI-refactor regression
receipt: the current discovery contains 215 tests and the independent GUI
verification ran the full suite twice with `215 tests, OK (skipped=1)`. The
gated native COM test is the single skip when `HWPX_RUN_COM_TESTS` is unset.

Final independent PDF wiring receipt:

```text
python -m unittest discover -s tests -p "test_pdf_mode_wiring.py"  # twice
Ran 12 tests ... OK
Ran 12 tests ... OK

python -m unittest discover -s tests -p "test_pdf_layout_mode.py"
Ran 9 tests ... OK
python -m unittest discover -s tests -p "test_pdf_hwp_image_writer.py"
Ran 12 tests ... OK
python -m unittest discover -s tests -p "test_runtime_capabilities.py"
Ran 7 tests ... OK
python -m unittest discover -s tests -p "test_conversion_diagnostics.py"
Ran 3 tests ... OK
```

Additional checks passed:

```text
python -m py_compile anyway_to_hwpx_com.py tests/test_pdf_mode_wiring.py
git diff --check
```

Manual `python anyway_to_hwpx_com.py --help` shows
`--pdf-mode {layout,editable}` and `(default: layout)`.

## Implemented contract

- CLI `--pdf-mode` defaults to `layout` and is explicitly threaded through
  `convert_file()`, `detect_and_parse()`, and `parse_pdf()`.
- Layout PDF parsing calls the public `render_pdf_layout()` renderer, bypasses
  all six editable postprocessors, and keeps a `TemporaryDirectory` under the
  output directory alive through page insertion and `SaveAs`.
- Editable parsing preserves ODL → pdfplumber → KORDOC → text fallback order.
  Direct `parse_pdf()` calls retain legacy editable behavior, while the
  conversion pipeline passes the layout default explicitly.
- `none` runtime capability rejects PDF input before the parser/renderer.
- Editable PDF conversion emits an actionable note when Java is below 11 or
  ODL is unavailable, while preserving the text fallback path.
- No global PDF mode or asset path state and no new direct HWPX XML write were
  introduced. Broad catches were removed from the touched PDF fallback seam.

## Adversarial and cleanup receipt

- Invalid mode is rejected with both supported values in the error.
- Layout text extractors are patched to fail if called; the test confirms they
  are bypassed.
- All six editable postprocessors are patched and confirmed not called for a
  layout image document.
- Success, build failure, and `SaveAs` failure all confirm the caller-owned
  `anyway-to-hwpx-pdf-*` directory is removed after the operation.
- A fake image insertion and fake `SaveAs` both observe the rendered image file
  while conversion is active, proving asset lifetime rather than path-only
  bookkeeping.
- Named `OSError`/`RuntimeError` build and save failures are wrapped with the
  source filename and stage context; no broad exception catch was introduced.
- Repeated wiring runs are deterministic; no persistent mode/asset state leaks
  between tests.
- Editable formatting remains on the existing editable finalization path
  (including the existing 160% line-spacing and paragraph-spacing helpers).
  Layout image pages do not receive those postprocessors; the Todo 6 writer
  owns the remaining COM-level editable character/spacing and Korean
  noun-postposition contract.

No commit or staging was performed.
