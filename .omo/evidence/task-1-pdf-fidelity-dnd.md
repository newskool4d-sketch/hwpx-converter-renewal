# Task 1 Evidence: IBM Carbon UI Contract

## Pre-flight

Command: `git rev-parse --show-toplevel`

Output:

```text
C:/Users/홍주형/.claude/hwpx-converter-renewal
```

The expected repository root matched. Initial dirty baseline from `git status --short` was:

```text
 D "dist/Anyway_to_hwpx(2026. 6. 11.).zip"
?? .omo/
?? gui_preview.png
?? samples/sample_complex.md
```

Protected paths were not edited. Final targeted status remained:

```text
 D "dist/Anyway_to_hwpx(2026. 6. 11.).zip"
?? gui_preview.png
?? samples/sample_complex.md
```

Other concurrent Wave 1 work added untracked files after the baseline and was preserved.

## TDD RED to GREEN

### Slice 1: semantic constants

RED command: `python -m unittest discover -s tests -p "test_ui_design_contract.py"`

```text
ERROR: test_semantic_colors_match_carbon_contract
ModuleNotFoundError: No module named 'ui_design'
Ran 1 test in 0.008s
FAILED (errors=1)
```

Minimal GREEN implementation: four exact public constants in `ui_design.py`.

```text
.
Ran 1 test in 0.009s
OK
```

### Slice 2: font fallback and flat geometry

RED command: `python -m unittest discover -s tests -p "test_ui_design_contract.py"`

```text
ERROR: test_font_fallback_and_flat_geometry_are_public_contracts
AttributeError: module 'ui_design' has no attribute 'UI_FONT_FAMILY'
Ran 2 tests in 0.017s
FAILED (errors=1)
```

Minimal GREEN implementation: `UI_FONT_FAMILY` and `UI_GEOMETRY`.

```text
..
Ran 2 tests in 0.015s
OK
```

### Slice 3: exact state map, semantic reverse map, and immutability

RED command: `python -m unittest discover -s tests -p "test_ui_design_contract.py"`

```text
ERROR: test_state_colors_are_complete_immutable_and_semantic_only
AttributeError: module 'ui_design' has no attribute 'UI_STATE_COLORS'
Ran 3 tests in 0.007s
FAILED (errors=1)
```

Minimal GREEN implementation: a `MappingProxyType` map with only action/focus/info/drop-valid Blue, success Green, warning/drop-partial Yellow, and error/drop-rejected Red.

```text
...
Ran 3 tests in 0.012s
OK
```

## Automated verification

Command run twice to detect flakiness:

```text
python -m unittest discover -s tests -p "test_ui_design_contract.py"
...
Ran 3 tests in 0.008s
OK

python -m unittest discover -s tests -p "test_ui_design_contract.py"
...
Ran 3 tests in 0.009s
OK
```

The exact test output, not only the process exit status, was inspected. It reports all three public-contract tests as passed.

`python -m py_compile ui_design.py tests\test_ui_design_contract.py` completed with exit code 0.

No-excuse review command:

```text
python C:\Users\홍주형\.codex\plugins\cache\sisyphuslabs\omo\4.15.1\skills\programming\scripts\python\check-no-excuse-rules.py ui_design.py tests\test_ui_design_contract.py
no violations in 2 file(s)
```

The review applies to these newly added Python files even though the surrounding legacy project uses `unittest` and does not otherwise follow the newer tooling convention.

## Manual QA

Command:

```text
python -c "import ui_design; print(ui_design.UI_STATE_COLORS); print(ui_design.UI_FONT_FAMILY)"
```

Observable output after explicitly setting the Windows console/Python UTF-8 output encoding:

```text
{'action': '#0F62FE', 'focus': '#0F62FE', 'info': '#0F62FE', 'drop-valid': '#0F62FE', 'success': '#24A148', 'warning': '#F1C21B', 'drop-partial': '#F1C21B', 'error': '#DA1E28', 'drop-rejected': '#DA1E28'}
('IBM Plex Sans', '맑은 고딕', 'Arial', 'sans-serif')
```

PASS: all four semantic colors and the IBM Plex Sans to 맑은 고딕 fallback chain are visible.

## Adversarial probes

| Probe | Result |
| --- | --- |
| Malformed input | N/A. This module exposes constants and immutable mappings; it has no input parser. |
| Stale state | PASS. The test mutates `dict(UI_STATE_COLORS)` and confirms the module's `action` color remains `ACTION_BLUE`. |
| Direct mutation | PASS. Assigning through `UI_STATE_COLORS` raises `TypeError`. |
| Dirty worktree | PASS. Baseline protected paths match their final targeted status exactly. |
| Flaky tests | PASS. The complete contract suite passed twice in separate invocations. |
| Misleading success | PASS. The exact unittest output was inspected and all three named tests ran. |

## Scope and cleanup

No processes, external dependencies, images, or temporary assets were created. No staging or commit was performed.

`rg -n "#[0-9A-Fa-f]{6}" anyway_to_hwpx_gui.py` still finds legacy raw colors at lines 27 through 38, 84, 99, and 163. This is intentionally unresolved: replacing them belongs to Todo 7, and this task was explicitly prohibited from editing `anyway_to_hwpx_gui.py`.
