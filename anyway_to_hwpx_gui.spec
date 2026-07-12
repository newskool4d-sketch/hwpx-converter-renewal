# -*- mode: python ; coding: utf-8 -*-
import os

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)

pdf_stack = os.environ.get('HWPX_GUI_PDF_STACK', 'full').lower()
if pdf_stack not in {'full', 'text', 'none'}:
    raise SystemExit('HWPX_GUI_PDF_STACK must be one of: full, text, none')

pdf_text_imports = [] if pdf_stack == 'none' else ['pdfplumber', 'fitz', 'pymupdf', 'pypdf']
odl_imports = [
    'opendataloader_pdf',
    'opendataloader_pdf.runner',
    'opendataloader_pdf.wrapper',
    'opendataloader_pdf.convert_generated',
    'opendataloader_pdf.cli_options_generated',
    'importlib.resources',
] if pdf_stack == 'full' else []

# 기능 유지형 경량화: 변환에 직접 쓰는 의존성은 유지하고,
# PyMuPDF/table 훅 등에서 끌려오는 분석/노트북/이미지 계열 대형 의존성만 제외한다.
excluded_modules = [
    'IPython',
    'jupyter',
    'matplotlib',
    'notebook',
    'numpy',
    'pandas',
    'PIL',
    'scipy',
    'setuptools._distutils',
    'sklearn',
    'test',
    'tests',
    'torch',
    'tensorflow',
]

# opendataloader_pdf 패키지에서 JAR 파일 경로를 동적으로 탐색
def _find_odl_jar():
    try:
        import importlib.resources as _r
        ref = _r.files("opendataloader_pdf").joinpath("jar", "opendataloader-pdf-cli.jar")
        with _r.as_file(ref) as p:
            return str(p)
    except Exception:
        return None

_odl_jar = _find_odl_jar() if pdf_stack == 'full' else None
_odl_datas = [(_odl_jar, "opendataloader_pdf/jar")] if _odl_jar else []

# tkinterdnd2 ships the native tkdnd DLL and Tcl support files inside its
# package.  Collect all three surfaces explicitly so drag-and-drop survives
# one-file/one-dir builds.  Pillow is deliberately excluded below; PyMuPDF's
# Pixmap.tobytes("png") path does not need PIL.
_tkdnd_datas = collect_data_files("tkinterdnd2")
_tkdnd_binaries = collect_dynamic_libs("tkinterdnd2")
_tkdnd_hiddenimports = collect_submodules("tkinterdnd2")

a = Analysis(
    ['anyway_to_hwpx_gui.py'],
    pathex=[],
    binaries=_tkdnd_binaries,
    datas=_odl_datas + _tkdnd_datas,
    hiddenimports=pdf_text_imports + odl_imports + _tkdnd_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_modules,
    noarchive=True,
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='anyway_to_hwpx_gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
