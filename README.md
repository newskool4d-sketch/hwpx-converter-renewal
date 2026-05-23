# HWPX Converter Renewal

Markdown, TXT, DOCX, HTML, CSV, XLSX, and PDF files can be converted to HWPX through Hancom HWP COM automation.

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

Then select source files, choose an output folder, and start conversion.

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
python -m PyInstaller --onefile --windowed --name anyway_to_hwpx_gui --clean --hidden-import=pdfplumber --hidden-import=fitz --hidden-import=pymupdf .\anyway_to_hwpx_gui.py
```

Review PyInstaller warnings before distribution, especially optional PDF/OCR modules.
