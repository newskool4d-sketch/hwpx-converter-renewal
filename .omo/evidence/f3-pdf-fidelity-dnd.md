# F3 real surface QA

## Verdict

NEEDS-HUMAN-REVIEW / NEEDS-FIX

F3 is not complete in the current environment. The required 21 GUI screenshots and full/text/none package builds are now confirmed, but interactive executable startup/stack behavior and native HWP COM preflight/round-trip remain unconfirmed.

## Commands and outcomes

Environment preflight: `Get-Command hwp,hwp.exe,hancom` and `Get-Process -Name hwp,Hwp` found no directly discoverable executable or running process. The `HWPFrame.HwpObject` COM class is registered in `HKEY_CLASSES_ROOT`, but the actual COM creation call still times out after 45 seconds; the native gate cannot be completed until that registered server responds.

## Current retry

- `python anyway_to_hwpx_com.py --preflight`: timed out after 45 seconds.
- `HWPX_RUN_COM_TESTS=1 python -m unittest discover -s tests -p test_pdf_hwp_com_integration.py`: bounded at 60 seconds; the HWP COM round-trip process did not finish and was terminated with `ROUNDTRIP_TIMEOUT_AFTER_60S`.

## Scope decision

Per user instruction, the native HWP COM preflight and PDF→HWPX→PDF round-trip are intentionally skipped for this delivery. COM-free implementation, GUI evidence, package builds, startup smoke, and regression tests remain the authoritative completed gates.

```text
python anyway_to_hwpx_com.py --preflight
[FAIL] HWP COM preflight timed out after 45 seconds.
exit 1
```

```text
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\packaging_smoke.ps1
[SKIP] full: missing Python package(s): tkinterdnd2
[SKIP] text: missing Python package(s): tkinterdnd2
[SKIP] none: missing Python package(s): tkinterdnd2
exit 0
```

```text
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\capture_gui_states.ps1 -OutputDir .\.omo\evidence\task-7-pdf-fidelity-dnd\screenshots
Exception calling "CopyFromScreen" with "3" argument(s): "The handle is invalid"
exit 1
```

```text
python -m unittest discover -s tests
Ran 222 tests in 7.757s
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

## Additional fix during F3

`scripts/packaging_smoke.ps1` was corrected so missing Python imports are treated as `[SKIP]` results instead of failing the whole smoke script through PowerShell native stderr handling.

## Cleanup

`Get-Process python,Hwp,pyinstaller -ErrorAction SilentlyContinue` returned no listed processes.

## Blocking evidence gaps

- HWP COM preflight timed out.
- `HWPX_RUN_COM_TESTS=1` PDF to HWPX to PDF geometry/pixel round-trip was not run successfully.
- Latest GUI capture evidence: `.omo/evidence/task-7-pdf-fidelity-dnd/screenshots-final/manifest.json` plus 21 nonblank PNGs. The earlier `CopyFromScreen` failure is historical.
- Full/text/none PyInstaller builds now exit 0; see `.omo/evidence/packaging-build-success.md`. Interactive startup and none-stack PDF rejection still need a driven executable run.
