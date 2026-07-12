# Task 2 Code Quality Review

## Verdict

- `codeQualityStatus`: BLOCK
- `recommendation`: REQUEST_CHANGES
- reviewer verdict: needs-fix

## Skill Perspective Check

- `omo:remove-ai-slops`: loaded and applied to production and tests. The TkDND boundary helper/test pair violates this perspective because the helper is a pass-through wrapper with no boundary enforcement, and the test only mirrors tuple input.
- `omo:programming`: loaded with the Python reference and code-smells reference. The review applied the Python criteria for typed public APIs, no raw `dict`/`Any`/`object`, boundary parsing, and useful behavior tests. `unittest` is accepted for this task because the plan explicitly requires it for this legacy project.

## CRITICAL

- None.

## HIGH

- `gui_file_intake.py:143`: `input_paths_from_tkdnd_splitlist(split_paths: Sequence[str])` silently accepts a raw `str` because `str` satisfies `Sequence[str]` at runtime, and `tuple(raw_event_data)` splits it into characters. This does not enforce the required "TkDND raw data is interpreted only by `self.tk.splitlist(event.data)`" boundary and creates a failure mode for Todo 7 integration. Probe result:
  - Command: `python -c "from gui_file_intake import input_paths_from_tkdnd_splitlist; raw=r'{C:\\drop folder\\a file.pdf} {C:\\drop folder\\second file.md}'; result=input_paths_from_tkdnd_splitlist(raw); print(type(result).__name__, len(result), result[:12])"`
  - Result: `tuple 59 ('{', 'C', ':', '\\', 'd', 'r', 'o', 'p', ' ', 'f', 'o', 'l')`

- `tests/test_gui_file_intake.py:188`: the TkDND test is tautological. It passes a pre-split tuple to a pass-through helper and asserts it gets the same tuple back, so it does not fail if raw `event.data` is passed to the helper. This is false confidence against the strict splitlist acceptance criterion.

## MEDIUM

- `.omo/evidence/task-2-pdf-fidelity-dnd.md:23`: RED receipts are narrative claims, not real captured command output. Unlike Task 1 evidence, this file does not include traceback/error excerpts or paths to raw logs. The claimed RED states may be true, but they are not artifact-backed enough for the requested "real RED receipts" check.

- Current `git status --short` still includes ` D "dist/Anyway_to_hwpx(2026. 6. 11.).zip"`. Task evidence records this as a pre-existing protected baseline, and current status matches that claim, so I am not treating it as introduced by Task 2. It remains a scope-control risk for final F4 verification.

## LOW

- `gui_file_intake.py:143`: if the splitlist helper remains, it should do real boundary work or be removed. As written, it is a one-line wrapper around `tuple(...)`, which the remove-ai-slops perspective treats as needless abstraction unless it enforces the no-raw-data contract.

## Positive Checks

- `normalize_input_paths()` preserves order, canonicalizes paths with `resolve(strict=False)`, classifies missing/directory/unsupported inputs, and de-duplicates accepted candidates.
- `add_input_paths()` preserves caller-owned inputs, returns immutable tuples, reports busy with zero accepted paths, keeps duplicate order, and defaults output directory to the first accepted parent when blank.
- `gui_file_intake.py` imports neither `tkinter` nor `tkinterdnd2`.
- `rg -n "dict\\[|Dict\\[|Any|object|Mapping|MutableMapping|\\.split\\(|split\\(" gui_file_intake.py` returned no matches, so no raw dict/object/Any API or path whitespace split was found in the module.

## Verification Run

- `python -m unittest discover -s tests -p "test_gui_file_intake.py"`: PASS, `Ran 7 tests in 0.110s`, `OK`.
- Repeated `python -m unittest discover -s tests -p "test_gui_file_intake.py"`: PASS, `Ran 7 tests in 0.123s`, `OK`.
- `python -m py_compile gui_file_intake.py`: PASS.
- `git diff --check`: PASS.
- Manual spaced-path/category probe: PASS for normal split inputs. Output preserved `a file.pdf`, reported duplicate `a file.pdf`, rejected missing/directory/unsupported, and defaulted output to `drop folder`.

## Probe Matrix

- Malformed input: FAIL for raw TkDND string, which becomes characters instead of a rejected raw event payload.
- Stale state: PASS based on tests asserting caller list/tuple immutability and unchanged busy selection.
- Flaky tests: PASS for two independent focused unittest runs.
- Dirty worktree: WATCH. Protected deleted zip appears unchanged from evidence baseline, but final scope fidelity must compare against the original preflight.
- Misleading success: WATCH/BLOCKING EVIDENCE GAP. Green commands were independently rerun, but RED evidence is claim-only.
- Prompt injection: N/A; pure path metadata only, no file content or instruction interpretation.
- Cancel/resume: N/A; no worker lifecycle in this pure module.
- Hung operation: N/A; no network, subprocess, GUI loop, or unbounded blocking work beyond local filesystem metadata calls.

## Blockers

- Enforce or remove the TkDND splitlist boundary helper so raw `event.data` cannot be accepted as a `Sequence[str]` and split into characters.
- Replace the tautological splitlist test with behavior that fails on raw TkDND event strings and passes only already split path tuples/lists from `self.tk.splitlist(event.data)`.
- Add real RED receipts or raw log excerpts/paths to `.omo/evidence/task-2-pdf-fidelity-dnd.md`.
