# Task 2 — Shared file intake contract

## Pre-flight baseline

- Command: `git rev-parse --show-toplevel; git status --short`
- Repository root: `C:/Users/홍주형/.claude/hwpx-converter-renewal` (expected)
- Protected baseline (preserved):
  - ` D "dist/Anyway_to_hwpx(2026. 6. 11.).zip"`
  - `?? .omo/`
  - `?? gui_preview.png`
  - `?? samples/sample_complex.md`
- Result: expected repository and accepted dirty baseline; implementation limited to the assigned files.

## Contract derived before implementation

- `anyway_to_hwpx_com.py` declares the effective converter extensions as `.md`, `.txt`, `.docx`, `.html`, `.htm`, `.csv`, `.xlsx`, and `.pdf`.
- The existing picker preserves order, de-duplicates, and assigns the parent of the first selected file only when no output folder is already chosen.
- The pure intake contract will preserve those behaviors while additionally rejecting missing, directory, and unsupported paths; it will never mutate caller-owned sequences.

## TDD receipt

### RED 1 — public normalizer absent

Command: `python -m unittest discover -s tests -p "test_gui_file_intake.py"`

```text
ERROR: test_gui_file_intake (unittest.loader._FailedTest.test_gui_file_intake)
ModuleNotFoundError: No module named 'gui_file_intake'
Ran 1 test in 0.001s
FAILED (errors=1)
```

### RED 2 — state-combining API absent

Command: `python -m unittest discover -s tests -p "test_gui_file_intake.py"`

```text
ERROR: test_gui_file_intake (unittest.loader._FailedTest.test_gui_file_intake)
ImportError: cannot import name 'add_input_paths' from 'gui_file_intake'
Ran 1 test in 0.000s
FAILED (errors=1)
```

### RED 3 — duplicate reporting did not preserve candidate order

Command: `python -m unittest discover -s tests -p "test_gui_file_intake.py"`

```text
FAIL: test_reports_existing_and_incoming_duplicates_in_candidate_order
AssertionError: (added.pdf, existing.pdf) != (existing.pdf, added.pdf)
Ran 3 tests in 0.047s
FAILED (failures=1)
```

### RED 4 — raw TkDND event data was accepted as a character sequence

Command: `python -m unittest discover -s tests -p "test_gui_file_intake.py"`

```text
FAIL: test_rejects_raw_event_data_string_instead_of_treating_characters_as_paths
AssertionError: TypeError not raised
Ran 8 tests in 0.086s
FAILED (failures=1)
```

## Implemented contract

- `normalize_input_paths()` accepts a caller-owned path sequence plus caller-provided effective extensions. It returns frozen, tuple-backed accepted, duplicate, rejected, and busy categories; only regular files are accepted, and canonical `Path.resolve(strict=False)` values drive duplicate detection.
- `add_input_paths()` combines new paths with a caller-owned prior selection without mutation, reports busy with zero accepts, keeps multi-file candidate order, and selects the first newly accepted file's parent only when the output directory is blank.
- `input_paths_from_tkdnd_splitlist()` accepts only an already split `tk.splitlist(event.data)` result and rejects a raw `str` with `RawTkDndEventDataError` (`TypeError`) before it can be iterated as characters. The module imports neither `tkinter` nor `tkinterdnd2`.

## Automated verification

- Command 1: `python -m unittest discover -s tests -p "test_gui_file_intake.py"`
  - Result: `Ran 8 tests in 0.089s` / `OK`
- Command 2: `python -m unittest discover -s tests -p "test_gui_file_intake.py"`
  - Result: `Ran 8 tests in 0.081s` / `OK`
- Syntax and strict-rule audit: `python -m py_compile gui_file_intake.py tests\\test_gui_file_intake.py` and `python ...\\check-no-excuse-rules.py gui_file_intake.py tests\\test_gui_file_intake.py`
  - Result: `no violations in 2 file(s)`.
- `rg -n "tkinter|tkinterdnd2" gui_file_intake.py` exited 1 with no output, confirming no Tk imports.
- `git diff --check` returned clean.

## Manual QA

- Command: `python -c "from gui_file_intake import normalize_input_paths; import tempfile, pathlib; d=tempfile.TemporaryDirectory(); p=pathlib.Path(d.name)/'a file.pdf'; p.write_bytes(b'%PDF'); print(normalize_input_paths((str(p),), ('.pdf',)))"`
- Result: `NormalizedInputPaths(accepted=(WindowsPath('.../a file.pdf'),), duplicates=(), rejected=(), busy=())`.
- PASS: exactly one accepted path is present and the space in `a file.pdf` is preserved.
- Cleanup: `TemporaryDirectory` is owned by the one-shot process and is automatically removed when that process exits; no fixture directory was retained.
- Raw-data adversarial probe: `python -c "from gui_file_intake import input_paths_from_tkdnd_splitlist; print(input_paths_from_tkdnd_splitlist(r'{C:\\drop folder\\a file.pdf}'))"` exited 1 with `RawTkDndEventDataError: raw TkDND event data is not a split path sequence`; no whitespace or brace splitting occurred.

## Adversarial and scope checks

- Malformed input: tests cover missing paths, directories, unsupported extensions, canonical duplicates, and a valid path whose parent/file names contain spaces; categories and reasons are asserted.
- Stale state: tests assert unchanged caller lists while busy and unchanged caller tuples during multi-file intake; prior selection is returned as a new immutable tuple.
- Busy: tests assert zero accepted paths and an explicit `busy` category.
- Raw TkDND string: a non-tautological test and direct probe assert that raw `event.data` is rejected as `TypeError`, instead of being accepted as a `Sequence[str]` and split into characters.
- Multi-file order: tests assert accepted and duplicate source order plus first-accepted output-parent selection.
- Misleading success: tests and manual QA assert actual result categories, not only command exit codes.
- Flake check: the exact target suite passed twice independently.
- Dirty worktree: final `git status --short` retains the protected baseline entries unchanged: deleted `dist/Anyway_to_hwpx(2026. 6. 11.).zip`, untracked `gui_preview.png`, and untracked `samples/sample_complex.md`. Concurrent agents added other untracked owned artifacts; none were edited by this task.
- Prompt injection: N/A; this module reads filesystem path values only and interprets no instructions or content.
- Cancel/resume: N/A; the pure functions own no dialog or worker lifecycle.
- Hung operation: N/A; no network, subprocess, UI loop, or blocking I/O beyond bounded local filesystem metadata checks.

## DoneClaim

Shared pure picker/drop path intake is implemented in the assigned files and verified, including explicit raw-TkDND-string rejection. No files were staged or committed.
