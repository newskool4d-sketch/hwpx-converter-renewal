# Todo 8 evidence: packaging matrix, docs, and release smoke

## Packaging follow-up

Full, text, and none PyInstaller builds completed successfully after installing `tkinterdnd2==0.6.2`; artifact paths and exact results are recorded in `.omo/evidence/packaging-build-success.md`. The remaining gap is interactive startup/none-stack behavior, not build construction.

The smoke helper now derives the Python user site from `APPDATA` and the active interpreter version, preventing Windows profile encoding from producing a false missing-package result. A clean invocation of `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\packaging_smoke.ps1` reports PASS for all three stacks without a manually supplied `PYTHONPATH`.

## Scope and baseline

- Owned files: `anyway_to_hwpx_gui.spec`, `README.md`, `README.ko.md`, `scripts/packaging_smoke.ps1`, and this evidence file.
- Baseline was dirty before this task (`anyway_to_hwpx_com.py`, `anyway_to_hwpx_gui.py`, `requirements.txt` modified; `.omo/`, GUI modules, tests, and sample files untracked; the historical zip under `dist/` deleted). Those changes were preserved.

## RED / gap captured before editing

The original spec had `binaries=[]`, `datas=_odl_datas`, and `hiddenimports=pdf_text_imports + odl_imports`; it had no `tkinterdnd2` data/binary/hidden-import collection. It did contain `'PIL'` in `excluded_modules`, but the README did not explain why. The original English and Korean build sections only ran `python -m PyInstaller --clean .\\anyway_to_hwpx_gui.spec` and set `HWPX_GUI_PDF_STACK` to `text` or `none`; neither document had a full/text/none capability table, isolated `C:\\tmp` paths, Java 11 diagnostics, picker fallback, layout/editable trade-off, or editable formatting defaults.

## Implemented GREEN behavior

- The spec imports and calls `collect_data_files("tkinterdnd2")`, `collect_dynamic_libs("tkinterdnd2")`, and `collect_submodules("tkinterdnd2")`; those values feed `datas`, `binaries`, and `hiddenimports`. `PIL` remains excluded, while the PyMuPDF `Pixmap.tobytes("png")` layout path is documented and untouched.
- `README.md` and `README.ko.md` now describe the same matrix: `full` = layout + ODL-preferred editable with local fallback, `text` = layout + local text editable fallback without ODL, and `none` = PDF disabled before the worker. Both document Java 11+, the `java -version` diagnostic, DnD-to-picker fallback, layout/editable trade-offs, 200-DPI rendering, editable defaults (160% line spacing, paragraph-after 2, default char scale/spacing, Korean noun+postposition wrapping), and the absence of direct HWPX XML/cloud OCR. They also state that a shared PyMuPDF import may remain in a `none` executable for startup while capability filtering still rejects PDF before worker work.
- Exact build commands use `C:\\tmp\\hwpx-gui-<stack>\\dist` and `\\work` plus `--distpath`, `--workpath`, and `--specpath`; repository `dist/` and `build/` are not used.
- `scripts/packaging_smoke.ps1` is read-only by default. `-Build` is explicit, refuses to overwrite an existing temp root, isolates each stack, and verifies the executable exists after a zero PyInstaller exit code.

## Verification

Commands and observed results:

```text
python -c "import ast,pathlib; ... anyway_to_hwpx_gui.spec ..."
spec AST: PASS
spec source checks: PASS

pwsh -NoProfile -File .\\scripts\\packaging_smoke.ps1
[SKIP] full: missing Python package(s): tkinterdnd2
[SKIP] text: missing Python package(s): tkinterdnd2
[SKIP] none: missing Python package(s): tkinterdnd2
helper exit=0

PowerShell parser: scripts/packaging_smoke.ps1
script parse: PASS

git diff --check
PASS (only normal LF/CRLF conversion warnings)
```

Installed build probes: PyInstaller `6.20.0` and `opendataloader_pdf` are present; `tkinterdnd2` is not installed. Therefore exact full/text/none PyInstaller builds were intentionally skipped for the precise dependency reason above. No `C:\\tmp\\hwpx-gui-*` package directories were created.

## Adversarial checks

- Dirty-worktree safety: no unrelated files were reverted or staged.
- Misleading build success: the helper requires both exit code 0 and `anyway_to_hwpx_gui.exe` at the requested isolated dist path.
- Existing temp output: `-Build` refuses an existing `C:\\tmp\\hwpx-gui-<stack>` rather than deleting or overwriting it.
- Long-build/cleanup boundary: default mode performs no build and creates no package directory; explicit `-Build` writes only to the caller-selected `C:\\tmp` root.
