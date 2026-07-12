# Todo 3 Code Quality Review

## Status

- codeQualityStatus: BLOCK
- recommendation: REQUEST_CHANGES
- verdict: needs-fix

## Skill-Perspective Check

- `omo:remove-ai-slops` loaded and applied: checked production/test diff for claim-only tests, tautological removal checks, needless production parsing/normalization, hidden cache/temp ownership, and scope drift.
- `omo:programming` loaded with Python reference and code-smells reference: checked Python maintainability, typed boundaries, error shape, parameter count, file size, and behavior-oriented tests.
- Result: production code and tests do not violate these perspectives in a blocker way. The blocker is evidence quality, not the `pdf_layout.py` contract implementation.

## Findings

### CRITICAL

- None.

### HIGH

- `.omo/evidence/task-3-pdf-fidelity-dnd.md:20` - `.omo/evidence/task-3-pdf-fidelity-dnd.md:30`: RED evidence is summarized as a table of snippets, not captured failing command output or trace excerpts. The requested acceptance explicitly required actual RED output, not claim-only evidence. Blocker: add artifact-backed failing test runs with command, failure output, and enough context to prove each RED failed for the intended reason.

- `.omo/evidence/task-3-pdf-fidelity-dnd.md:52` - `.omo/evidence/task-3-pdf-fidelity-dnd.md:60`: Manual QA claims a synthetic two-page A4 render and cleanup but gives no reproducible command or artifact path. My independent manual probe attempts did not complete: one failed due a malformed temp path in the review harness, and two normalized `C:/tmp` probes hung until I killed the verifier Python process. The unit test covers equivalent two-page behavior, but the manual-QA evidence remains non-reproducible. Blocker: replace the claim with a reproducible command transcript or a bounded script invocation showing two returned paths under the caller asset dir and cleanup after return.

### MEDIUM

- None.

### LOW

- `git diff --check` passed, but because `pdf_layout.py` and `tests/test_pdf_layout_mode.py` are untracked, the exact command does not check those files. I manually inspected the untracked submitted files for forbidden imports and direct HWPX/XML/cache/temp patterns.

## Verification Run

- `python -m unittest discover -s tests -p "test_pdf_layout_mode.py"`: PASS, 9 tests in 0.736s.
- Rerun `python -m unittest discover -s tests -p "test_pdf_layout_mode.py"`: PASS, 9 tests in 1.414s.
- `python -m py_compile pdf_layout.py`: PASS.
- `git diff --check`: PASS.
- Pure LOC for `pdf_layout.py`: 128.

## Contract Review

- `pdf_layout.py` defines public `layout`/`editable` mode parsing, 200 DPI RGB PyMuPDF rendering, immutable page blocks with point dimensions, caller-owned existing asset directory validation, uniform geometry rejection, and a 500 MiB default output cap.
- No Pillow, OCR, text overlay, persistent raster cache, direct HWPX XML, or internal temp directory create/delete was found in `pdf_layout.py`.
- Tests are behavior-focused through public API calls and cover malformed input, missing/non-writable asset dirs, cap overflow, mixed geometry, editable parsing, invalid mode guidance, caller cleanup, and two-page A4 RGB/200 DPI output.

## Blockers

- Replace claim-only RED evidence with actual failing command output.
- Replace non-reproducible manual QA claim with a reproducible bounded command/script transcript proving caller-owned paths and cleanup.
