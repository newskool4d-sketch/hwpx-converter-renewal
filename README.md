# HWPX Converter Renewal

Markdown, TXT, DOCX, HTML, CSV, XLSX, and PDF files can be converted to HWPX through Hancom HWP COM automation.

## Files

- `anyway_to_hwpx_com.py`: CLI conversion engine.
- `anyway_to_hwpx_gui.py`: Tkinter GUI wrapper.
- `dist/anyway_to_hwpx_gui.exe`: one-file Windows GUI executable.
- `dist/사용방법.txt`: end-user usage guide.
- `samples/`: small sample input files.
- `verification-log.md`: local verification history.

## Requirements

For end users:

- Hancom Office HWP installed on Windows.
- Working `HWPFrame.HwpObject` COM automation.
- OCR tool such as `kordoc-ai` or Tesseract is needed for scanned image PDFs.

For rebuilding:

- Python
- pywin32
- PyInstaller
- python-docx
- beautifulsoup4
- openpyxl
- pdfplumber
- PyMuPDF

## CLI Usage

```powershell
python anyway_to_hwpx_com.py "input.md" -o "C:\output"
```

Optional end mark insertion:

```powershell
python anyway_to_hwpx_com.py "input.md" -o "C:\output" --insert-end-mark
```

## GUI Usage

Run:

```text
dist\anyway_to_hwpx_gui.exe
```

Then select source files, choose an output folder, and start conversion.

Existing HWPX files are not overwritten. The converter appends ` - 2`, ` - 3`, and so on.

## Build

```powershell
python -m PyInstaller --onefile --windowed --name anyway_to_hwpx_gui --clean --hidden-import=pdfplumber --hidden-import=fitz --hidden-import=pymupdf .\anyway_to_hwpx_gui.py
```
