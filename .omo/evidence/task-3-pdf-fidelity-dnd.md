# Todo 3 — PDF mode and caller-owned layout assets

## Baseline acknowledgement

- Repository root: `C:/Users/홍주형/.claude/hwpx-converter-renewal`.
- Accepted protected baseline before this task: deleted `dist/Anyway_to_hwpx(2026. 6. 11.).zip`, untracked `.omo/`, `gui_preview.png`, and `samples/sample_complex.md`.
- The parent task owner confirmed this is expected. These protected paths were not edited by this task.

## Delivered contract

- `PdfMode` is a strongly typed `StrEnum` with exactly `layout` and `editable`; `parse_pdf_mode()` gives actionable unsupported-mode errors.
- `render_pdf_layout()` accepts a caller-owned existing writable asset directory and uses PyMuPDF only to create 200 DPI RGB PNG page images.
- `RenderedPdfLayout` returns immutable `PdfPageImageBlock` values with image paths and source point dimensions.
- Mixed page dimensions/orientations are rejected before PNG persistence and direct callers are guided to `editable` mode.
- Output is capped at 500 MiB by default; the public optional cap is used only to exercise the boundary deterministically in tests.
- The renderer creates no temporary directory, deletes no caller directory, writes only `page-####.png` children, and has no raster cache, Pillow, OCR, text overlay, or HWPX XML work.

## TDD receipts

Each test uses public output/errors rather than private helpers. Captured RED-to-GREEN slices:

| Behavior | RED evidence | GREEN evidence |
| --- | --- | --- |
| A4 2-page layout rendering | `ModuleNotFoundError: pdf_layout` | 2 RGB PNGs at 200 DPI with 595×842 point blocks |
| Editable mode parsing | missing `parse_pdf_mode` import | `PdfMode.EDITABLE` returned |
| Invalid mode guidance | raw `ValueError` | `PdfModeError` includes `layout` and `editable` |
| Mixed geometry | `MixedPageGeometryError not raised` | error before asset persistence |
| Output limit | `RenderedOutputLimitError not raised` | capped output leaves asset directory empty |
| Missing asset directory | missing actionable `create it` guidance | caller directory is not created and error is actionable |

Additional public adversarial tests cover malformed PDFs, non-writable asset directories, no writes outside the caller asset directory, and caller-controlled cleanup.

## Automated verification

```text
python -m unittest discover -s tests -p "test_pdf_layout_mode.py"  # run 1
.........
Ran 9 tests in 1.106s
OK

python -m unittest discover -s tests -p "test_pdf_layout_mode.py"  # run 2
.........
Ran 9 tests in 1.506s
OK

python -m py_compile pdf_layout.py
# exit 0
```

`pdf_layout.py` is 128 pure LOC, below the 250 LOC contract.

## Manual QA

Created a synthetic 2-page A4 PDF with PyMuPDF in a caller-created temporary directory, rendered it through the public API, inspected its returned values, then cleaned that caller directory.

```text
pages=2 dpi=200 color_mode=RGB image_paths=page-0001.png,page-0002.png under_caller_asset_dir=True
```

PASS: returned page count is 2, DPI is 200, color mode is RGB, and both reported image paths are children of the caller-created asset directory. The command cleaned the temporary directory after the return.

## Adversarial and lifecycle checks

| Check | Result |
| --- | --- |
| Malformed input | PASS — `PdfInputError`; no asset children created. |
| Mixed dimensions/orientation | PASS — `MixedPageGeometryError` advises editable mode before writes. |
| Missing/non-writable asset directory | PASS — contextual `AssetDirectoryError`; no asset children created. |
| 500 MiB output guard | PASS — deterministic low-cap test exercises the exact public guard and prevents partial writes. |
| Stale state / persistent cache | PASS — only source PDF and caller asset directory exist after success; caller cleanup removes all assets. |
| Flaky rerun | PASS — prescribed test command passed twice. |
| Misleading success | PASS — generated PNGs are re-opened by PyMuPDF and asserted `n == 3`, `alpha == 0`, and 200-DPI A4 pixel dimensions. |
| Dirty worktree | PASS — accepted baseline was preserved; no protected baseline path was edited. |
| Prompt injection | N/A — this pure local renderer has no model, instruction channel, or external service. |
| Cancel/resume | N/A — no asynchronous job lifecycle exists in this rendering contract; later caller integration owns it. |
| Hung operation | N/A — finite local page iteration only; no network, subprocess, or polling behavior. |

## Cleanup

All synthetic PDFs and PNG assets were created inside `TemporaryDirectory` fixtures. Every fixture and manual-QA caller directory was cleaned after use. No fixture or rendered asset remains in the repository.

## DoneClaim

Todo 3 is complete: the typed PDF layout contract, caller-owned raster asset lifetime, 200 DPI RGB PyMuPDF rendering, geometry refusal, output cap, and contextual diagnostics are implemented and verified without staging or committing.
