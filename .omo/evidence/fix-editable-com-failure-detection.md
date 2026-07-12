# Editable HWP COM failure detection

## Change

- `InsertText`, `BreakPara`, `CharShape`, and `TableCreate` now reject explicit COM failure returns through `_require_hwp_success`.
- Added one behavioral regression test per operation.

## TDD evidence

Each test was run before its implementation change and failed because no `RuntimeError` was raised (the table case instead continued until `ParagraphShape`). Each passed after its corresponding production change.

## Verification

- `python -m unittest discover -s tests -p test_pdf_hwp_image_writer.py` — 16 tests, OK.
- `python -m unittest discover -s tests` — 220 tests, OK, 1 skipped native COM integration gate.
- `python -m py_compile anyway_to_hwpx_com.py tests\test_pdf_hwp_image_writer.py` — exit 0.
- `git diff --check` — exit 0; line-ending warnings only.
- The programming no-excuse checker reports 63 legacy structural/style findings in the 2,519-pure-LOC module/test fixture. No unchecked-return finding remains in the four changed operations.

## Remaining native gates

- HWP COM preflight/roundtrip cannot be proven because preflight times out.
- GUI screenshots cannot be captured because Windows `CopyFromScreen` reports an invalid handle.
- Packaged runtime matrix remains skipped until `tkinterdnd2` is installed.
