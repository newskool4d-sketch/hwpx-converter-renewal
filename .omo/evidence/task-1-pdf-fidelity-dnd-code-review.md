# Task 1 Code Quality Review: IBM Carbon UI Contract

Verdict: confirmed

## Scope Reviewed

- Plan item: Todo 1 in `.omo/plans/pdf-fidelity-dnd.md`
- Files reviewed: `DESIGN.md`, `ui_design.py`, `tests/test_ui_design_contract.py`, `.omo/evidence/task-1-pdf-fidelity-dnd.md`
- Baseline GUI scan: `anyway_to_hwpx_gui.py`
- Report path: `.omo/evidence/task-1-pdf-fidelity-dnd-code-review.md`

## Skill-Perspective Check

- `omo:remove-ai-slops` loaded and applied as a review lens.
- `omo:programming` loaded; `references/python/README.md` also consulted for Python-specific review criteria.
- Result: no remove-ai-slops violation found. The tests are not deletion-only, removal-verification, tautological, or false-confidence tests; they pin the requested public token contract. The production module does not introduce needless parsing, normalization, abstractions, or speculative logic.
- Result: no programming-perspective violation found for this bounded contract module. Constants use `Final`; mappings are immutable with `MappingProxyType`; there are no `Any`, `object`, broad exceptions, variant chains, or boundary validation smells. `unittest` is accepted here because the plan explicitly names Python `unittest` for this legacy project.

## Findings

### CRITICAL

None.

### HIGH

None.

### MEDIUM

None.

### LOW

None.

## Artifact-Backed Checks

- Todo 1 exact constants are present in `ui_design.py:6` through `ui_design.py:9`: `#0F62FE`, `#24A148`, `#F1C21B`, `#DA1E28`.
- IBM Plex to Korean fallback is present in `ui_design.py:10` through `ui_design.py:15` and asserted in `tests/test_ui_design_contract.py:13` through `tests/test_ui_design_contract.py:21`.
- Flat geometry is documented in `DESIGN.md:8` through `DESIGN.md:10`, exported in `ui_design.py:16` through `ui_design.py:18`, and tested in `tests/test_ui_design_contract.py:20` through `tests/test_ui_design_contract.py:21`.
- Full semantic state mapping is exported in `ui_design.py:19` through `ui_design.py:31` and tested in `tests/test_ui_design_contract.py:23` through `tests/test_ui_design_contract.py:56`.
- Reverse semantic color restriction is tested in `tests/test_ui_design_contract.py:39` through `tests/test_ui_design_contract.py:49`.
- Direct mutation protection is tested in `tests/test_ui_design_contract.py:51` through `tests/test_ui_design_contract.py:52`; independent probe returned `TypeError`.
- Stale copied-map probe is tested in `tests/test_ui_design_contract.py:54` through `tests/test_ui_design_contract.py:56`; independent probe printed original `#0F62FE`, copied `#DA1E28`, then `True`.
- `DESIGN.md:37` is the only case-insensitive generic Green/Yellow/Red prose hit in the new design files, and it is the explicit prohibition against decorative/generic use.
- `git diff -- anyway_to_hwpx_gui.py` was empty. Legacy raw GUI colors remain in `anyway_to_hwpx_gui.py:27` through `anyway_to_hwpx_gui.py:38` and `anyway_to_hwpx_gui.py:240` through `anyway_to_hwpx_gui.py:241`; this matches the parent verification instruction that raw-color GUI cleanup belongs to Todo 7, not Todo 1.
- Evidence file contains real RED proof rather than self-report: `.omo/evidence/task-1-pdf-fidelity-dnd.md:36` through `.omo/evidence/task-1-pdf-fidelity-dnd.md:42`, `.omo/evidence/task-1-pdf-fidelity-dnd.md:55` through `.omo/evidence/task-1-pdf-fidelity-dnd.md:61`, and `.omo/evidence/task-1-pdf-fidelity-dnd.md:74` through `.omo/evidence/task-1-pdf-fidelity-dnd.md:80`.
- Evidence file records adversarial probes at `.omo/evidence/task-1-pdf-fidelity-dnd.md:137` through `.omo/evidence/task-1-pdf-fidelity-dnd.md:146`.

## Commands Run

```text
Get-Content -LiteralPath C:\Users\홍주형\.codex\plugins\cache\sisyphuslabs\omo\4.15.1\skills\remove-ai-slops\SKILL.md
Get-Content -LiteralPath C:\Users\홍주형\.codex\plugins\cache\sisyphuslabs\omo\4.15.1\skills\programming\SKILL.md
Get-Content -LiteralPath C:\Users\홍주형\.codex\plugins\cache\sisyphuslabs\omo\4.15.1\skills\programming\references\python\README.md
Get-Content -LiteralPath C:\Users\홍주형\AGENTS.md
Get-Content -LiteralPath .omo\plans\pdf-fidelity-dnd.md
Get-Content -LiteralPath DESIGN.md
Get-Content -LiteralPath ui_design.py
Get-Content -LiteralPath tests\test_ui_design_contract.py
Get-Content -LiteralPath .omo\evidence\task-1-pdf-fidelity-dnd.md
git status --short
git diff -- DESIGN.md ui_design.py tests/test_ui_design_contract.py
git diff --stat
rg -n "#[0-9A-Fa-f]{6}" anyway_to_hwpx_gui.py
rg -n -i "\b(green|yellow|red)\b" DESIGN.md ui_design.py tests\test_ui_design_contract.py
python -m unittest discover -s tests -p "test_ui_design_contract.py"
python -m unittest discover -s tests -p "test_ui_design_contract.py"
python -m py_compile ui_design.py
python -c "import ui_design; copied=dict(ui_design.UI_STATE_COLORS); copied['action']=ui_design.ERROR_RED; print(ui_design.UI_STATE_COLORS['action']); print(copied['action']); print(ui_design.UI_STATE_COLORS['action'] == ui_design.ACTION_BLUE)"
python -c 'import ui_design; exec("try:\n    ui_design.UI_STATE_COLORS[\"action\"] = ui_design.ERROR_RED\nexcept TypeError as exc:\n    print(type(exc).__name__)\nelse:\n    print(\"NO_ERROR\")")'
python C:\Users\홍주형\.codex\plugins\cache\sisyphuslabs\omo\4.15.1\skills\programming\scripts\python\check-no-excuse-rules.py ui_design.py tests\test_ui_design_contract.py
git diff -- anyway_to_hwpx_gui.py
git diff --check
git rev-parse --show-toplevel
```

## Command Results

- `python -m unittest discover -s tests -p "test_ui_design_contract.py"`: PASS, `Ran 3 tests`, `OK`.
- Repeated `python -m unittest discover -s tests -p "test_ui_design_contract.py"`: PASS, `Ran 3 tests`, `OK`.
- `python -m py_compile ui_design.py`: PASS, exit code 0.
- Stale-state copied-map probe: PASS, original remained `#0F62FE` after copy changed to `#DA1E28`.
- Direct mutation probe: PASS, returned `TypeError`.
- `check-no-excuse-rules.py ui_design.py tests\test_ui_design_contract.py`: PASS, `no violations in 2 file(s)`.
- `git diff -- anyway_to_hwpx_gui.py`: PASS, no output.
- `git diff --check`: PASS, no output.
- `git status --short`: dirty worktree remains present, including the protected deleted zip and untracked artifacts. No tracked GUI diff was present. Concurrent Wave 1 untracked files are outside this Todo 1 review.

## Adversarial Review

- `stale_state`: PASS. Both the test and an independent probe show copied-map mutation cannot alter the module mapping.
- `dirty_worktree`: PASS with caveat. The worktree is intentionally dirty; protected tracked GUI file has no diff, and the known deleted zip remains a pre-existing dirty path.
- `flaky_tests`: PASS. The requested contract test passed in two separate invocations.
- `misleading_success`: PASS. The evidence file includes concrete RED failures and command outputs.
- `malformed_input`: N/A. `ui_design.py` has no input parser or boundary.

## Status

- `codeQualityStatus`: CLEAR
- `recommendation`: APPROVE
- `blockers`: None.
