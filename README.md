# HWPX Converter Renewal

**English** | [한국어](README.ko.md)

Convert Markdown, TXT, DOCX, HTML, CSV, XLSX, and PDF into HWPX through Hancom HWP COM automation. Use the desktop GUI for conversion, or open its local document tools to read, compare, validate, preview, and edit existing documents.

**[Version 2026.10.13](https://github.com/newskool4d-sketch/hwpx-converter-renewal/releases/tag/v2026.10.13)** adds document tools powered by kordoc, conversion cancellation, per-file time limits, and failed-file retry. The existing conversion engine and document templates remain available without kordoc.

## Download

| Download | Use it for |
| --- | --- |
| **[Windows x64 ZIP — recommended](https://github.com/newskool4d-sketch/hwpx-converter-renewal/releases/download/v2026.10.13/hwpx-converter-v2026.10.13-windows-x64.zip)** | Conversion **and document tools**. Includes the EXE, pinned document-tool dependencies, and guides. Extract the entire archive. |
| [Standalone EXE](https://github.com/newskool4d-sketch/hwpx-converter-renewal/releases/download/v2026.10.13/anyway_to_hwpx_gui.exe) | Basic conversion. Document-tool dependencies and Node.js are not bundled in this file. |
| [SHA256SUMS.txt](https://github.com/newskool4d-sketch/hwpx-converter-renewal/releases/download/v2026.10.13/SHA256SUMS.txt) | Verify downloaded files with SHA-256. |
| [release-manifest.json](https://github.com/newskool4d-sketch/hwpx-converter-renewal/releases/download/v2026.10.13/release-manifest.json) | Source commit, dependency versions, build information, and release test results. |

The ZIP includes **kordoc 4.21.30** and **pdfjs-dist 4.10.38**. It does not include Node.js or Hancom Office. ZIP users do not need to run `npm install`.

## Quick start

1. Install Hancom Office HWP on Windows 64-bit for conversion. Install **Node.js 20 or later** if you also want document tools.
2. Download the ZIP and extract **all files** into a folder you can write to.
3. Run `anyway_to_hwpx_gui.exe`. First startup can take tens of seconds; a clean-folder launch on the release verification PC took more than 45 seconds.
4. Select input files and an output folder, then start conversion. For PDF files, choose layout preservation or editable extraction.
5. To work with existing documents, click **`문서 읽기 · 비교 · 수정`** (read, compare, and edit documents).

Keep this folder structure together:

```text
extracted-folder/
├── anyway_to_hwpx_gui.exe
├── deps/
│   └── kordoc/
│       ├── package.json
│       ├── package-lock.json
│       └── node_modules/
└── docs/
    └── document-tools.md
```

Moving only the EXE keeps basic conversion available, but removes the adjacent dependencies needed by document tools.

## Features

| Feature | Behavior |
| --- | --- |
| Existing conversion | Seven default input formats, established Hancom output formatting, and layout/editable PDF modes. |
| Read and compare | Extract text and tables; inspect paragraph, cell, number, merge, and image differences. |
| Validate and inspect fields | Check HWPX structure and inspect form labels before filling them. |
| Fill forms and patch text | Preview JSON field values or edited Markdown, then save a **new HWPX copy**. |
| Preview | Open a local browser preview with page navigation and zoom. |
| Profile and lint | Extract a sample document's formatting profile and inspect Korean official-document notation. Profiles are not applied automatically. |
| Cancel and retry | Default **180-second limit per conversion file**, cancellation, and retry of failed or unprocessed files. Successful outputs remain available. |
| Local images | Insert standalone local Markdown images and DOCX body images. |

Document reading supports multiple formats; editing, field inspection, validation, and formatting profiles focus on HWPX. See the [document tools guide (Korean)](docs/document-tools.md) for details.

## Requirements

| Component | When needed |
| --- | --- |
| Windows 64-bit | Released desktop application. |
| Hancom Office HWP with working `HWPFrame.HwpObject` COM automation | Creating HWPX through the converter and checking actual Hancom output. |
| Node.js 20+ and the ZIP's `deps/kordoc` folder | Local document tools and the optional kordoc input engine. Document tools themselves do not require Hancom. |
| Java 11+ | Optional OpenDataLoader extraction for editable PDF conversion. Local fallback extraction remains available without Java. |
| Python and project requirements | Running source code, CLI commands, tests, or builds. Not needed to run the released EXE. |

The published Windows build uses the `full` PDF stack. The app does not install or update Node.js or document dependencies automatically.

## Using the GUI

### Conversion

Select files, choose an output folder, and start conversion. Existing HWPX files are preserved: new filenames receive ` - 2`, ` - 3`, and so on.

The optional **`저장 폴더 비우기(앱 관리 파일만)`** setting clears only outputs recorded in the app's manifest. The converter refuses a non-empty folder if it contains unlisted files or lacks the required manifest.

Each conversion runs in a separate worker process. On cancellation or timeout, the app allows up to two seconds for graceful shutdown before ending its own worker. It does not terminate all Hancom processes. If Hancom itself stops responding, a remaining window may need attention.

### Document tools

Open **`문서 읽기 · 비교 · 수정`**, then use the relevant action:

1. **Read** a source document and optionally save its Markdown.
2. **Compare** two documents or **validate** an HWPX file.
3. For **form filling**, inspect fields and load a JSON file such as `{"사업명": "생태 체험", "참가 인원": "30명"}`.
4. For **text patching**, edit the exported Markdown and load it back.
5. Preview the proposed edit, then save to a new HWPX path. If inputs change after preview, preview them again.

Source fingerprints are checked before saving. Existing document files cannot be overwritten, and incomplete or unsupported edits are not saved. GUI report and Markdown exports use the save dialog's overwrite confirmation.

### PDF modes

- **Layout preservation** inserts each page as a 200-DPI RGB image through PyMuPDF. The visual layout is preserved; the page content is not editable text.
- **Editable extraction** creates searchable HWP paragraphs and tables. Complex positioning, fonts, and scanned pages may need further work.

The default editable PDF path rebuilds content through COM rather than directly importing HWPX XML. Its defaults include 160% line spacing, paragraph-after spacing 2, default character scale/spacing, and Korean noun-plus-postposition wrapping protection.

The `full` stack prefers `opendataloader-pdf` when Java 11+ is available. Otherwise, the GUI reports the diagnostic and uses the installed local `pdfplumber`/PyMuPDF/pypdf fallback. Check Java with `java -version`.

### Limits and troubleshooting

- The SVG preview can differ from Hancom's screen and printed output. Structure validation, content comparison, and actual Hancom inspection are separate checks.
- The new document integration works offline. It does not download OCR models or web images, register MCP servers, run watch webhooks, or use Chromium PDF printing. OCR is not bundled; the existing separately configured OCR path remains available.
- Equations, charts, images inside tables, nested tables, and some original formatting are not fully supported. Read the reported warnings. Hyperlink display text is retained, but clickable links and all emphasis formatting are not preserved.
- If document tools cannot find Node.js or kordoc, keep `deps/kordoc` beside the EXE and run the tool's diagnostic. Custom locations can be supplied with `HWPX_NODE_PATH` and `HWPX_KORDOC_HOME`. Basic conversion remains available.
- This release is not digitally signed. Use the official release assets and compare `Get-FileHash .\anyway_to_hwpx_gui.exe -Algorithm SHA256` with `SHA256SUMS.txt`.

## CLI usage

These commands run from a source checkout after the developer setup below.

### Existing converter

```powershell
python anyway_to_hwpx_com.py --preflight
python anyway_to_hwpx_com.py --list-formats
python anyway_to_hwpx_com.py "input.md" -o "C:\output"
python anyway_to_hwpx_com.py "input.md" -o "C:\output" --insert-end-mark
python anyway_to_hwpx_com.py "input.md" -o "C:\output" --empty-output-folder
```

`--empty-output-folder` only clears an app-managed folder whose contents are all listed in its manifest.

The optional kordoc input engine accepts **HWP, HWPX, HWPML, XLS, XLSX, DOCX, PPTX, and PDF**, rebuilding extracted content in the converter's output format. This is separate from editing an existing HWPX while retaining its structure:

```powershell
python anyway_to_hwpx_com.py "source.hwpx" --input-engine kordoc -o "C:\output"
```

For the existing external OCR integration, use `--kordoc-home "C:\tools\kordoc-ai"` or set `$env:KORDOC_HOME = "C:\tools\kordoc-ai"` before converting a scanned PDF. This OCR location is separate from the new document tools' `HWPX_KORDOC_HOME`.

### Local document commands

```powershell
python document_cli.py diagnose
python document_cli.py parse "source.hwpx" --report "read.json"
python document_cli.py compare "before.hwpx" "after.hwpx" --report "comparison.json"
python document_cli.py validate "source.hwpx"
python document_cli.py fields "form.hwpx"
python document_cli.py fill "form.hwpx" --values-file "values.json"
python document_cli.py fill "form.hwpx" --values-file "values.json" --apply --output "filled.hwpx"
python document_cli.py patch "source.hwpx" --markdown-file "edited.md"
python document_cli.py patch "source.hwpx" --markdown-file "edited.md" --apply --output "patched.hwpx"
python document_cli.py render "source.hwpx" --page 1 --report "preview.json"
python document_cli.py profile "sample.hwpx" --report "profile.json"
python document_cli.py lint "source.hwpx"
```

`fill` and `patch` default to dry runs. Writing requires both `--apply` and a new `--output` path. Reports also require a new file path. Responses contain `ok`, `status`, `action`, `data`, `warnings`, and `error`; exit codes are **0** success, **1** error, **2** partial, and **130** cancelled. `render` returns SVG inside JSON. The document CLI has its own default timeout of 120 seconds, adjustable with `--timeout`.

To compare local PDF text extraction without OCR:

```powershell
python scripts\compare_pdf_engines.py "document.pdf" --report "pdf-comparison.json"
```

Add `--reference "reviewed-text.txt"` to measure token precision and recall against a reviewed reference. Agreement between engines is not accuracy; reading order, table structure, and visual fidelity require separate review. This command does not change the default PDF engine.

## Developer guide

### Source map and setup

| Path | Purpose |
| --- | --- |
| `anyway_to_hwpx_com.py` / `anyway_to_hwpx_gui.py` | Conversion entry point and Tkinter GUI. |
| `conversion_process.py` / `gui_conversion_worker.py` | Isolated conversion, cancellation, and worker coordination. |
| `document_cli.py` / `document_workbench.py` | JSON CLI and desktop document tools. |
| `kordoc_client.py` / `kordoc_bridge.mjs` | Local Python-to-Node document bridge. |
| `document_ir.py` | Structured document input for conversion. |
| `samples/` / `tests/` | Sample inputs, unit tests, and optional native integration tests. |
| `verification-log.md` / `docs/` | Verification history, usage, and implementation records. |

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Optional document tools; requires Node.js 20+ and npm:
.\scripts\install_kordoc.ps1
```

The installer pins dependencies in `deps/kordoc`, uses the lockfile when available, and excludes lifecycle scripts and optional dependencies. It does not modify an existing MCP installation. Generated `dist/`, `build/`, `out/`, `__pycache__/`, and `node_modules/` contents are not tracked.

### Verification

The [v2026.10.13 release](https://github.com/newskool4d-sketch/hwpx-converter-renewal/releases/tag/v2026.10.13) passed **399 checks, with no skips**, including actual Hancom PDF integration. Its release notes describe sample output comparisons and packaged-app checks; these are results from the verification PC, not a guarantee for every Windows environment.

```powershell
python -m unittest discover -s tests
python -m py_compile anyway_to_hwpx_com.py anyway_to_hwpx_gui.py document_cli.py
```

The normal suite skips the opt-in native Hancom PDF test. On a Windows machine with Hancom, close any open Hancom documents before explicitly enabling it:

```powershell
$env:HWPX_RUN_COM_TESTS = "1"
python -m unittest discover -s tests
Remove-Item Env:HWPX_RUN_COM_TESTS
python anyway_to_hwpx_com.py --preflight
python anyway_to_hwpx_com.py samples\sample.md -o out
```

### PDF stack matrix

The spec (`HWPX_GUI_PDF_STACK`) and runtime capability report use the same values:

| Stack | Layout PDF | Editable PDF | ODL / Java | PDF intake |
| --- | --- | --- | --- | --- |
| `full` (default) | PyMuPDF page images | ODL preferred; local text fallback | Bundles `opendataloader-pdf`; Java 11+ enables ODL | Enabled |
| `text` | PyMuPDF page images | `pdfplumber`/PyMuPDF/pypdf fallback | No ODL; Java not required | Enabled |
| `none` | No | No | No ODL/text stack | Disabled before the conversion worker |

In a `none` build, the GUI removes PDF from picker/drop acceptance and disables both PDF controls; the CLI rejects PDF before rendering or starting PDF work. A shared PyMuPDF import may still be included for startup. Its presence does not enable PDF conversion.

### Build and package

Use isolated paths under `C:\tmp\hwpx-gui-<stack>` for each stack, keeping verification builds away from the repository's `dist/` and `build/`:

```powershell
$stack = "full" # full, text, or none
$root = "C:\tmp\hwpx-gui-$stack"
$env:HWPX_GUI_PDF_STACK = $stack
python -m PyInstaller --clean --noconfirm `
  --distpath "$root\dist" --workpath "$root\work" `
  .\anyway_to_hwpx_gui.spec
.\scripts\packaging_smoke.ps1
```

`packaging_smoke.ps1` checks all three stacks without building. Add `-Build` to opt into isolated builds; the helper refuses an existing `C:\tmp\hwpx-gui-<stack>` directory and checks that the EXE was produced.

The spec bundles the Node bridge, but **not** Node.js or `deps/kordoc`. To distribute document tools, copy the installed `deps/kordoc` folder and usage/security guides beside the EXE in a staging folder matching the ZIP layout above. Keep dependency license and copyright files under `node_modules`, and archive the whole staged folder.

The spec collects `tkinterdnd2` data, native binaries, and hidden imports. If drag-and-drop is unavailable, the app falls back to the standard file picker. Pillow is excluded: PDF layout rendering uses PyMuPDF's direct `Pixmap.tobytes("png")` path.

Review PyInstaller warnings, especially optional PDF/OCR modules. An exit code of 0 alone does not prove the build works: verify the requested EXE exists and its main window launches.

### Release checklist

1. Set `__version__` in `anyway_to_hwpx_com.py` to `YYYY.MM.DD`; use `+dev` between releases.
2. Run unit/syntax checks and the relevant native Hancom checks. Record skipped or unavailable checks explicitly.
3. Convert a real sample, run `python scripts/hwpx_editor_safety_gate.py <output>`, and open it in Hancom to inspect margins, fonts, tables, and print output.
4. Build in an isolated path. Confirm a responsive window titled `HWPX 변환기...`, no unhandled-exception dialog, and normal shutdown. Allow time for first-start extraction.
5. Verify the packaged worker and adjacent document dependencies from an extracted ZIP. Preserve licenses, check ZIP contents, and record artifact sizes, SHA-256 hashes, and source commit.
6. Attach the EXE, ZIP, checksums, and release manifest to a GitHub Release tagged at the build's source commit. Recheck published downloads. Do not commit generated binaries.
