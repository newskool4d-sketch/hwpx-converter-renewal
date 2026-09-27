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


# Tcl/Tk 9(CPython 3.14.7+ Windows)은 라이브러리를 DLL 내장 zipfs(//zipfs:/lib/...)에 두어
# PyInstaller 6.20 훅이 _tcl_data/_tk_data를 수집하지 못하고, 런타임 훅은 두 폴더가 없으면
# 시작 시 FileNotFoundError로 종료한다(IMPROVEMENT_PLAN N15). 빌드 시 zipfs 내용을 workpath에
# 복사해 같은 이름으로 번들한다. 라이브러리가 일반 폴더(Tcl 8.6 등)면 아무것도 하지 않는다.
def _tcl_tk_zipfs_datas():
    import shutil
    import tkinter

    probe = tkinter.Tk()
    probe.withdraw()
    try:
        libraries = {'_tcl_data': probe.eval('info library'), '_tk_data': probe.eval('set tk_library')}
        if not all(path.startswith('//zipfs:') for path in libraries.values()):
            return []
        out_root = os.path.join(workpath, 'tcl_tk_zipfs')
        shutil.rmtree(out_root, ignore_errors=True)
        os.makedirs(out_root)
        datas = []
        for dest, source in libraries.items():
            target = os.path.join(out_root, dest)
            probe.eval('file copy {%s} {%s}' % (source, target.replace('\\', '/')))
            for folder, _dirs, files in os.walk(target):
                rel = os.path.relpath(folder, out_root)
                datas += [(os.path.join(folder, name), rel) for name in files]
        return datas
    finally:
        probe.destroy()


_tcl_tk_datas = _tcl_tk_zipfs_datas()

a = Analysis(
    ['anyway_to_hwpx_gui.py'],
    pathex=[],
    binaries=_tkdnd_binaries,
    datas=_odl_datas + _tkdnd_datas + _tcl_tk_datas,
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
