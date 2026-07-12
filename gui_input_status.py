from __future__ import annotations

import os
from pathlib import Path
from tkinter import messagebox

from gui_file_intake import RejectionReason


def report_input_result(app, result) -> None:
    details = []
    if result.duplicates:
        details.append(f"중복 {len(result.duplicates)}개")
    if result.rejected:
        labels = {
            RejectionReason.MISSING: "없는 경로",
            RejectionReason.NOT_A_FILE: "폴더",
            RejectionReason.UNSUPPORTED_EXTENSION: "지원하지 않는 형식",
        }
        reasons = sorted({labels[item.reason] for item in result.rejected})
        details.append(f"거부 {len(result.rejected)}개({', '.join(reasons)})")
    summary = f"{len(result.accepted)}개 추가됨"
    if details:
        summary += " · " + " · ".join(details)
    visible_summary = summary if result.accepted or details else "파일을 선택하세요."
    app.status.set(visible_summary)
    if result.rejected:
        tag = "err"
    elif result.duplicates:
        tag = "warn"
    elif result.accepted:
        tag = "info"
    else:
        tag = "muted"
    app._append_log(visible_summary, tag)


def finish_conversion(app, completed, failures) -> None:
    app.progress.configure(value=completed)
    app._set_busy(False)
    if failures:
        app.status.set(f"완료 {completed}개 · 실패 {len(failures)}개")
        lines = [
            f"• {Path(target).name if target != 'HWP 실행' else target}: {error}"
            for target, error in failures[:5]
        ]
        if len(failures) > 5:
            lines.append(f"... 외 {len(failures) - 5}개")
        messagebox.showerror(
            "변환 실패",
            f"완료 {completed}개, 실패 {len(failures)}개입니다.\n\n"
            + "\n".join(lines)
            + "\n\n자세한 내용은 로그를 확인하세요.",
        )
    else:
        app.status.set(f"전체 변환 완료: {completed}개")
        open_folder = messagebox.askyesno(
            "변환 완료",
            f"{completed}개 파일을 변환했습니다.\n저장 폴더를 열까요?",
        )
        if open_folder:
            out_dir = app.output_dir.get().strip()
            if out_dir and os.path.isdir(out_dir):
                os.startfile(out_dir)
