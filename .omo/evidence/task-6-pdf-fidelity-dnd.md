# Todo 6 — HWP COM page-image writer and editable defaults

## Protected baseline

The worktree was already dirty before this task. Existing GUI/runtime/PDF-layout
changes, the deleted distribution ZIP, and prior `.omo` evidence were preserved.
Only `anyway_to_hwpx_com.py`, the two Todo 6 test files, and this evidence file
were owned by this task.

## TDD receipt

Initial fake-COM RED run:

```text
python -m unittest discover -s tests -p "test_pdf_hwp_image_writer.py"
Ran 12 tests ...
FAILED (failures=1, errors=11)
Missing configure_pdf_page_setup/insert_pdf_page_images, InsertPicture false
was not rejected, and editable ParagraphShape defaults were not emitted.
```

After implementation:

```text
python -m unittest discover -s tests -p "test_pdf_hwp_image_writer.py"
Ran 12 tests in 0.061s
OK
```

## Implemented contract

- `configure_pdf_page_setup()` uses `CreateAction("PageSetup")`, `CreateSet()`,
  `GetDefault()`, and nested `Item("PageDef")`; dimensions are min source
  width/max source height × 100, orientation follows width > height, and all
  page margins/header/footer/gutter values are zero.
- `insert_pdf_page_images()` inserts each page with `sizeoption=1` and point→mm
  conversion, issuing `BreakPage` only between pages.
- Explicit `False` COM results and exceptions fail the layout build with source
  context. No editable fallback is attempted.
- Layout mode calls none of the six editable postprocessors; editable mode
  retains all six.
- Editable ParagraphShape sends 160% line spacing, 2pt default `NextSpacing`,
  and `BreakNonLatinWord=0`; character ratio/spacing properties are untouched,
  preserving HWP defaults and Korean noun+postposition wrapping.
- No HWPX XML image writer was added; XML is read only by the gated integration
  assertions.

## Verification

```text
python -m unittest discover -s tests -p "test_pdf_hwp_image_writer.py"
Ran 12 tests ... OK

python -m unittest discover -s tests -p "test_pdf_mode_wiring.py"
Ran 12 tests ... OK

python -m unittest discover -s tests -p "test_conversion_diagnostics.py"
Ran 3 tests ... OK

python -m unittest discover -s tests -p "test_core.py"
Ran 95 tests ... OK

python -m unittest discover -s tests -p "test_pdf_hwp_com_integration.py"
Ran 1 test ... OK (skipped=1; HWPX_RUN_COM_TESTS is not set)

python -m unittest discover -s tests
Ran 215 tests in 10.954s
OK (skipped=1)

python -m py_compile anyway_to_hwpx_com.py tests/test_pdf_hwp_image_writer.py tests/test_pdf_hwp_com_integration.py
git diff --check
```

Native HWP COM export and pixel round-trip remain gated on a Windows host with
Hancom HWP and `HWPX_RUN_COM_TESTS=1`.
