# Packaging build evidence

## Environment

- Python 3.14.3
- PyInstaller 6.20.0
- `tkinterdnd2==0.6.2` installed in the user site directory; the Windows user profile path required an `APPDATA`-based `PYTHONPATH` because the default path was mojibake-encoded by the shell.

## Commands

Each command used the matching `HWPX_GUI_PDF_STACK` value and isolated `C:\tmp\hwpx-gui-<stack>\{build,dist}` paths:

```text
python -m PyInstaller --clean --noconfirm --distpath C:\tmp\hwpx-gui-full\dist --workpath C:\tmp\hwpx-gui-full\build .\anyway_to_hwpx_gui.spec
python -m PyInstaller --clean --noconfirm --distpath C:\tmp\hwpx-gui-text\dist --workpath C:\tmp\hwpx-gui-text\build .\anyway_to_hwpx_gui.spec
python -m PyInstaller --clean --noconfirm --distpath C:\tmp\hwpx-gui-none\dist --workpath C:\tmp\hwpx-gui-none\build .\anyway_to_hwpx_gui.spec
```

All three commands exited 0 and reported `Build complete!`.

## Artifacts

| stack | executable | size |
|---|---|---:|
| full | `C:\tmp\hwpx-gui-full\dist\anyway_to_hwpx_gui.exe` | 81,273,712 bytes |
| text | `C:\tmp\hwpx-gui-text\dist\anyway_to_hwpx_gui.exe` | 58,788,829 bytes |
| none | `C:\tmp\hwpx-gui-none\dist\anyway_to_hwpx_gui.exe` | 58,788,829 bytes |

The spec uses one-file mode, so TkDND runtime files are embedded in the executable rather than visible as separate files in `dist`.

## Remaining limitation

This proves package construction, not interactive executable startup or native HWP COM round-trip. Those remain separate F3 gates.

## Startup smoke

Each generated executable was launched hidden for five seconds. All three processes remained alive for the full interval (`full`, `text`, `none`) and were then explicitly stopped for cleanup. No immediate import/runtime exit occurred.
