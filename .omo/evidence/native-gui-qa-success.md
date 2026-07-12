# Native GUI QA

- Result: 21 fresh Tk window screenshots captured with Windows `PrintWindow`.
- Manifest: `.omo/evidence/task-7-pdf-fidelity-dnd/screenshots/manifest.json`.
- States: default, valid-drop, invalid-drop, busy, success, warning, error.
- Sizes: 760×620, 800×680, 1200×900.
- All PNGs are nonblank and have distinct SHA-256 hashes.
- Full regression after the final UI text edit: 221 tests OK, 1 native HWP COM test skipped.
- Package smoke remains skipped because `tkinterdnd2` is not installed.
- HWP COM round-trip remains pending after the prior 45-second preflight timeout.

The legacy `native-qa.txt` is stale and encoded as non-UTF-8; this UTF-8 evidence file supersedes it.
