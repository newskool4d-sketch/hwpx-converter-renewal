# Fix: close HWP document when layout build fails

## Finding

F2 found that `convert_file()` created a HWP document and only closed it inside the `SaveAs` `finally` block. A failure in `insert_pdf_page_images()` or `build_doc()` before `SaveAs` could leave the HWP document open.

## Change

- Added fake document close-call tracking in `tests/test_pdf_mode_wiring.py`.
- Added `test_layout_build_failure_closes_created_document_once`.
- Restructured `anyway_to_hwpx_com.py` so the HWP document is closed by an outer `finally` after document creation, while keeping separate contextual errors for layout build and save failures.

## Verification

```text
python -m unittest discover -s tests -p "test_pdf_mode_wiring.py"
.............
----------------------------------------------------------------------
Ran 13 tests in 3.160s

OK
```

```text
python -m py_compile anyway_to_hwpx_com.py
PASS
```

## Residual risk

- This evidence covers the document-close leak on build failures and the existing save-failure path.
- It does not resolve F3 native HWP COM round-trip, GUI screenshot, or packaged executable smoke-test blockers.
