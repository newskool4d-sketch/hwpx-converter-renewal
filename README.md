# HWPX Converter Renewal

**English** | [한국어](README.ko.md)

Markdown, TXT, DOCX, HTML, CSV, XLSX, and PDF files can be converted to HWPX through Hancom HWP COM automation.

## Download

Get the standalone GUI executable from the [latest release](https://github.com/newskool4d-sketch/hwpx-converter-renewal/releases/latest):

- **`anyway_to_hwpx_gui.exe`** — no installation required (Windows 64-bit, Hancom Office HWP must be installed)

Download it, run it, select source files, choose an output folder, and start conversion.

## User Guide

### Requirements

- Windows
- Hancom Office HWP installed
- Working `HWPFrame.HwpObject` COM automation
- For PDF input: use a build with the `full` or `text` PDF stack (see the matrix below)
- For scanned image PDFs: an OCR tool such as `kordoc-ai` (the converter does not bundle OCR)

PDF support has two levels:

- **Layout**: renders each page as a 200-DPI RGB image through PyMuPDF. This preserves the visual page layout, but the inserted page is not editable text.
- **Editable**: extracts text and tables into HWP paragraphs/tables. This is searchable and editable, but complex positioning, fonts, and scanned pages cannot be reproduced exactly. Scanned image PDFs still require OCR.

The GUI's editable defaults are intentional: 160% line spacing, paragraph-after spacing 2, default character scale/spacing, and Korean noun-plus-postposition wrapping protection. There is no direct HWPX XML import and no cloud OCR service.

For the `full` stack, `opendataloader-pdf` is preferred for editable extraction when Java 11+ is available. If Java is missing or older, the GUI reports the diagnostic and uses the local `pdfplumber`/PyMuPDF/pypdf editable fallback when those libraries are present. Check the runtime diagnostic with:

```powershell
java -version
```

Java 11 or newer is required for the ODL path; Java is not required for the `text` fallback path.

### GUI Usage

Run the GUI executable if you have a local build:

```text
dist\anyway_to_hwpx_gui.exe
```

Then select source files, choose an output folder, and start conversion. You can optionally enable "저장 폴더 비우기(앱 관리 파일만)" to clear only files recorded in the app manifest from a previous run.

Existing HWPX files are not overwritten. The converter appends ` - 2`, ` - 3`, and so on.

### CLI Usage

Check whether HWP COM automation is available before conversion:

```powershell
python anyway_to_hwpx_com.py --preflight
```

Convert one file:

```powershell
python anyway_to_hwpx_com.py "input.md" -o "C:\output"
```

Convert with optional end mark insertion:

```powershell
python anyway_to_hwpx_com.py "input.md" -o "C:\output" --insert-end-mark
```

Reuse an app-managed output folder as an empty folder:

```powershell
python anyway_to_hwpx_com.py "input.md" -o "C:\output" --empty-output-folder
```

`--empty-output-folder` refuses non-empty folders unless they contain this app's manifest and all existing files are listed in that manifest.

Use a custom OCR path for scanned PDFs:

```powershell
python anyway_to_hwpx_com.py "scan.pdf" -o "C:\output" --kordoc-home "C:\tools\kordoc-ai"
```

Or set an environment variable:

```powershell
$env:KORDOC_HOME = "C:\tools\kordoc-ai"
python anyway_to_hwpx_com.py "scan.pdf" -o "C:\output"
```

List supported input formats:

```powershell
python anyway_to_hwpx_com.py --list-formats
```

## Developer Guide

### Files

- `anyway_to_hwpx_com.py`: CLI conversion engine.
- `anyway_to_hwpx_gui.py`: Tkinter GUI wrapper.
- `requirements.txt`: Python dependencies for development and rebuilds.
- `samples/`: small sample input files.
- `tests/`: COM-free parser, table layout, output path, and OCR path tests.
- `verification-log.md`: local verification history.

Generated files are intentionally not tracked:

- `dist/`
- `build/`
- `out/`
- `__pycache__/`

### Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Test

Run tests that do not require Hancom HWP:

```powershell
python -m unittest discover -s tests
```

Run syntax checks:

```powershell
python -m py_compile anyway_to_hwpx_com.py anyway_to_hwpx_gui.py
```

Manual HWP COM verification still requires Hancom HWP on Windows:

```powershell
python anyway_to_hwpx_com.py --preflight
python anyway_to_hwpx_com.py samples\sample.md -o out
```

### PDF stack matrix

The same three values are used by the spec (`HWPX_GUI_PDF_STACK`) and by the runtime capability report:

| Stack | Layout PDF | Editable PDF | ODL / Java | PDF intake |
| --- | --- | --- | --- | --- |
| `full` (default) | Yes, PyMuPDF page images | Yes, ODL preferred; local text fallback if ODL is unavailable | Bundles `opendataloader-pdf`; Java 11+ enables ODL | Enabled |
| `text` | Yes, PyMuPDF page images | Yes, `pdfplumber`/PyMuPDF/pypdf fallback; no ODL | Java not required | Enabled |
| `none` | No | No | No ODL/text stack (shared runtime imports may remain) | Disabled before conversion worker |

`layout` trades editability for page fidelity. `editable` trades exact positioning for searchable, editable HWP content. In a `none` build the GUI removes `.pdf` from picker and drop acceptance and disables both PDF mode controls; the CLI rejects PDF input before rendering or starting PDF work.

The GUI and converter share importable modules, so a `none` executable may still contain a shared PyMuPDF import needed for startup. That does not enable PDF conversion: capability filtering removes PDF intake and the converter rejects PDF before the worker performs PDF work.

### Build GUI executable

Use isolated paths under `C:\tmp\hwpx-gui-<stack>` for every stack. Do not allow PyInstaller to write the repository's `dist\` or `build\` directories:

```powershell
$stack = "full" # full, text, or none
$root = "C:\tmp\hwpx-gui-$stack"
$env:HWPX_GUI_PDF_STACK = $stack
python -m PyInstaller --clean --noconfirm `
  --distpath "$root\dist" --workpath "$root\work" --specpath (Get-Location) `
  .\anyway_to_hwpx_gui.spec
```

Run all three source/dependency checks without building:

```powershell
.\scripts\packaging_smoke.ps1
```

To opt into isolated builds through the helper, use `.\scripts\packaging_smoke.ps1 -Build`. The helper refuses to overwrite an existing `C:\tmp\hwpx-gui-<stack>` directory and verifies that a reported-success build produced `anyway_to_hwpx_gui.exe`.

The spec explicitly collects `tkinterdnd2` data, native binaries, and hidden imports. If that optional package is absent at runtime, the GUI falls back to the standard file picker; drag-and-drop is unavailable but conversion remains usable. Pillow is intentionally excluded: the layout path keeps PyMuPDF's direct `Pixmap.tobytes("png")` save path and does not require PIL.

Review PyInstaller warnings before distribution, especially optional PDF/OCR modules. A build is not successful merely because PyInstaller exits 0; confirm the executable exists under the requested `C:\tmp` dist path and inspect warnings.
