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
- For text PDFs: bundled or installed PDF text libraries such as `pdfplumber` or `PyMuPDF`
- For scanned image PDFs: an OCR tool such as `kordoc-ai`

PDF support has two levels:

- Text PDF: extracts embedded text with Python PDF libraries.
- Scanned image PDF: requires OCR. Configure the OCR path with `--kordoc-home` or `KORDOC_HOME`.

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

### Build GUI Executable

```powershell
python -m PyInstaller --clean .\anyway_to_hwpx_gui.spec
```

The spec defaults to `HWPX_GUI_PDF_STACK=full`, which bundles the structured PDF extraction path and text PDF fallback libraries. Smaller builds can opt out of part of the PDF stack:

```powershell
$env:HWPX_GUI_PDF_STACK = "text"
python -m PyInstaller --clean .\anyway_to_hwpx_gui.spec

$env:HWPX_GUI_PDF_STACK = "none"
python -m PyInstaller --clean .\anyway_to_hwpx_gui.spec
```

Review PyInstaller warnings before distribution, especially optional PDF/OCR modules.
