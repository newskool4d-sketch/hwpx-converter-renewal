from __future__ import annotations

import argparse
from pathlib import Path
import sys
import tempfile
from typing import assert_never

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from anyway_to_hwpx_gui import ConverterApp


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", choices=("default", "valid-drop", "invalid-drop", "busy", "success", "warning", "error"), default="default")
    parser.add_argument("--width", type=int, default=800)
    parser.add_argument("--height", type=int, default=680)
    parser.add_argument("--hold-seconds", type=float, default=1.5)
    args = parser.parse_args()

    app = ConverterApp()
    app.title(f"HWPX GUI QA - {args.state}-{args.width}x{args.height}")
    app.maxsize(max(args.width, 2000), max(args.height, 2000))
    app.geometry(f"{args.width}x{args.height}")
    with tempfile.TemporaryDirectory(prefix="hwpx-gui-state-") as temporary_directory:
        root = Path(temporary_directory)
        match args.state:
            case "default":
                pass
            case "valid-drop":
                valid = root / "valid source.md"
                valid.write_text("# valid", encoding="utf-8")
                app._add_input_paths((str(valid),))
            case "invalid-drop":
                invalid = root / "invalid source.rtf"
                invalid.write_text("unsupported", encoding="utf-8")
                app._add_input_paths((str(invalid),))
            case "busy":
                app._set_busy(True)
                app.status.set("변환 중에는 파일 목록을 변경할 수 없습니다.")
            case "success":
                app.status.set("전체 변환 완료: 2개")
                app._append_log("완료: source.hwpx", "ok")
            case "warning":
                app.status.set("확인이 필요한 입력이 있습니다.")
                app._append_log("확인 필요: PDF 스캔 문서", "warn")
            case "error":
                app.status.set("변환 실패: 입력 형식을 확인하세요.")
                app._append_log("실패: invalid source.pdf", "err")
            case unreachable:
                assert_never(unreachable)
        app.update_idletasks()
        app.after(round(args.hold_seconds * 1000), app.destroy)
        app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
