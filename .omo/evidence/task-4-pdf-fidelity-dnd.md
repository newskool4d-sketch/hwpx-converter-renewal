# Todo 4 evidence: runtime capability and PDF stack contract

## Scope and protected baseline

Pre-flight commands:

```text
git rev-parse --show-toplevel
C:/Users/홍주형/.claude/hwpx-converter-renewal

git status --short
 D "dist/Anyway_to_hwpx(2026. 6. 11.).zip"
?? .omo/
?? DESIGN.md
?? gui_file_intake.py
?? gui_preview.png
?? pdf_layout.py
?? samples/sample_complex.md
?? tests/test_gui_file_intake.py
?? tests/test_pdf_layout_mode.py
?? tests/test_ui_design_contract.py
?? ui_design.py
```

The deleted distribution zip and unrelated untracked artifacts were preserved.

## TDD receipt

Initial RED run after adding `tests/test_runtime_capabilities.py` and before
adding the module:

```text
ImportError: Failed to import test module: test_runtime_capabilities
ModuleNotFoundError: No module named 'runtime_capabilities'
```

After implementing `runtime_capabilities.py`:

```text
python -m unittest discover -s tests -p "test_runtime_capabilities.py"
.......
----------------------------------------------------------------------
Ran 7 tests in 0.003s

OK
```

The mandated second run also passed:

```text
python -m unittest discover -s tests -p "test_runtime_capabilities.py"
.......
----------------------------------------------------------------------
Ran 7 tests in 0.003s

OK
```

Additional checks:

```text
python -m py_compile runtime_capabilities.py
<no output; exit 0>
git diff --check
<no output; exit 0>
```

## Manual matrix

Required Java 8 fallback command:

```text
mode=text layout_enabled=True editable_enabled=True odl_enabled=False editable_fallback_enabled=True pdf_disabled=False dnd_enabled=False
```

This confirms layout remains enabled, editable fallback remains enabled, ODL
is disabled, and PDF input is not disabled.

None-stack command:

```text
mode=none layout_enabled=False editable_enabled=False odl_enabled=False editable_fallback_enabled=False pdf_disabled=True dnd_enabled=False
```

This confirms the PDF-disabled matrix. Its effective extension set omits
`.pdf`; full/text sets retain `.pdf`.

## Dependency feasibility

`requirements.txt` now pins:

```text
tkinterdnd2==0.6.2
opendataloader-pdf==2.4.7
```

No package installation or network download was attempted, per task
instruction. Existing environment probes reported:

```text
tkinterdnd2_spec= None
opendataloader_pdf_spec= ModuleSpec(...opendataloader_pdf...)
opendataloader_pdf_import=ok
tkinterdnd2_import= False
```

Therefore ODL is already importable in this environment, while tkinterdnd2
would require a later approved install. The runtime contract treats DnD as an
independent optional capability and preserves picker/layout/text behavior.

## Adversarial and cleanup receipt

- Strict-literal malformed module values are rejected as unavailable rather
  than truthiness-enabled; the test covers this path.
- Malformed Java output and missing Java return `None`; Java versions below 11
  disable only ODL, preserving layout/text fallback.
- `detect_capabilities()` probes each call and returns a frozen value; no mode
  or asset path is kept in module-global mutable state.
- `probe_java_major()` uses `subprocess.run(..., timeout=5.0)` and catches only
  expected missing/timeout/process/OS errors.
- No temporary directories or generated assets were created by this todo.
- No commit or staging was performed.
