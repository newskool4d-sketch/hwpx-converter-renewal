from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from gui_file_intake import add_input_paths, input_paths_from_tkdnd_splitlist
from gui_conversion_worker import ConversionSnapshot, converter, pythoncom, run_conversion, time
from gui_input_status import finish_conversion, report_input_result
from gui_layout import build_ui, configure_styles, make_card
from gui_theme import SUPPORTED_EXTENSIONS, SUPPORTED_PATTERNS
from runtime_capabilities import RuntimeCapabilities, detect_capabilities

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    DND_FILES = None
    TkinterDnD = None

BaseTk = TkinterDnD.Tk if TkinterDnD is not None else tk.Tk


from gui_theme import (
    ACCENT,
    ACCENT_DARK,
    ACCENT_DIM,
    BG,
    BORDER,
    CARD,
    EDITABLE_FORMATTING_NOTICE,
    FONT,
    FONT_BOLD,
    FONT_SMALL,
    FONT_TITLE,
    GREEN,
    LOG_BG,
    MUTED,
    RED,
    TEXT,
    TROUGH,
)


class ConverterApp(BaseTk):
    def __init__(self, *, capabilities: RuntimeCapabilities | None = None):
        super().__init__()
        self.title("HWPX 변환기")
        self.geometry("800x680")
        self.minsize(700, 560)
        self.configure(bg=BG)

        self.files = []
        self.capabilities = capabilities or detect_capabilities()
        self.supported_extensions = tuple(
            extension
            for extension in SUPPORTED_EXTENSIONS
            if extension in self.capabilities.effective_gui_extensions
        )
        self.output_dir = tk.StringVar()
        self.empty_output_folder = tk.BooleanVar(value=False)
        self.insert_end_mark = tk.BooleanVar(value=False)
        self.pdf_mode = tk.StringVar(value="layout")
        self.status = tk.StringVar(value="파일을 선택하세요.")
        self.count_text = tk.StringVar(value="0개")
        self.messages = queue.Queue()
        self.worker = None
        self._busy = False

        self._init_styles()
        self._build_ui()
        self._register_drop_targets()
        self.after(100, self._poll_messages)

    def _init_styles(self):
        configure_styles(self)

    def _card(self, parent):
        return make_card(parent)

    def _build_ui(self):
        build_ui(self)

    # ─── 동작 ────────────────────────────────────────────────────────────────
    def _register_drop_targets(self):
        if DND_FILES is None:
            return
        for widget in (self.list_wrap, self.file_list):
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self._on_drop)

    def _is_busy(self):
        if self.worker and self.worker.is_alive():
            return True
        return self._busy

    def _set_busy(self, busy):
        self._busy = busy
        state = "disabled" if busy else "normal"
        pdf_state = "disabled" if busy or not getattr(self.capabilities, "pdf_enabled", True) else "normal"
        for control in (
            self.add_button,
            self.remove_button,
            self.clear_button,
            self.output_browse_button,
            self.empty_output_check,
            self.insert_end_check,
            self.convert_button,
        ):
            control.configure(state=state)
        self.pdf_layout_radio.configure(state=pdf_state)
        self.pdf_editable_radio.configure(state=pdf_state)
        self.out_entry.configure(state=state)

    def _supported_filetypes(self):
        if ".pdf" in self.supported_extensions:
            return SUPPORTED_PATTERNS
        return tuple(item for item in SUPPORTED_PATTERNS if "*.pdf" not in item[1])

    def _add_input_paths(self, input_paths):
        result = add_input_paths(
            tuple(input_paths),
            tuple(self.files),
            self.supported_extensions,
            is_busy=self._is_busy(),
            output_directory=self.output_dir.get(),
        )
        if result.busy:
            self.status.set("변환 중에는 파일 목록을 변경할 수 없습니다.")
            return result
        self.files = [str(path) for path in result.selection]
        self._refresh_file_list()
        if result.output_directory is not None and not self.output_dir.get().strip():
            self.output_dir.set(str(result.output_directory))
        self._report_input_result(result)
        return result

    def _report_input_result(self, result):
        report_input_result(self, result)

    def select_files(self):
        if self._is_busy():
            self.status.set("변환 중에는 파일 목록을 변경할 수 없습니다.")
            return
        selected = filedialog.askopenfilenames(title="변환할 파일 선택", filetypes=self._supported_filetypes())
        if not selected:
            return
        self._add_input_paths(selected)

    def _on_drop(self, event):
        if self._is_busy():
            self.status.set("변환 중에는 파일 목록을 변경할 수 없습니다.")
            return "break"
        try:
            split_paths = self.tk.splitlist(event.data)
            self._add_input_paths(input_paths_from_tkdnd_splitlist(split_paths))
        except (TypeError, tk.TclError) as exc:
            self.status.set(f"드롭을 읽지 못했습니다: {exc}")
        return "break"

    def clear_files(self):
        if self._is_busy():
            self.status.set("변환 중에는 파일 목록을 변경할 수 없습니다.")
            return
        self.files.clear()
        self._refresh_file_list()
        self.status.set("파일을 선택하세요.")

    def _remove_selected(self):
        if self._is_busy():
            self.status.set("변환 중에는 파일 목록을 변경할 수 없습니다.")
            return
        indices = sorted(self.file_list.curselection(), reverse=True)
        for idx in indices:
            del self.files[idx]
        self._refresh_file_list()
        count = len(self.files)
        self.status.set(f"{count}개 파일 선택됨" if count else "파일을 선택하세요.")

    def select_output_dir(self):
        if self._is_busy():
            self.status.set("변환 중에는 저장 폴더를 변경할 수 없습니다.")
            return
        selected = filedialog.askdirectory(title="저장 폴더 선택")
        if selected:
            self.output_dir.set(selected)

    def start_conversion(self):
        if self._is_busy():
            return
        if not self.files:
            messagebox.showwarning("확인", "변환할 파일을 선택하세요.")
            return
        if not self.output_dir.get().strip():
            messagebox.showwarning("확인", "저장 폴더를 선택하세요.")
            return
        if self.empty_output_folder.get():
            confirmed = messagebox.askyesno(
                "저장 폴더 비우기",
                "앱 manifest가 관리하는 기존 출력 파일만 삭제한 뒤 변환합니다.\n계속할까요?",
            )
            if not confirmed:
                return

        files = tuple(self.files)
        output_dir = self.output_dir.get().strip()
        empty_output_folder = bool(self.empty_output_folder.get())
        insert_end_mark = bool(self.insert_end_mark.get())
        pdf_mode = self.pdf_mode.get()
        self._set_busy(True)
        self.progress.configure(maximum=len(files), value=0)
        self.status.set("HWP 실행 중...")
        self._append_log("HWP 실행 중...", "muted")
        self.worker = threading.Thread(
            target=self._convert_worker,
            args=(files, output_dir, empty_output_folder, insert_end_mark, pdf_mode),
            daemon=True,
        )
        self.worker.start()

    def _convert_worker(self, files, output_dir, empty_output_folder, insert_end_mark, pdf_mode):
        snapshot = ConversionSnapshot(
            files=tuple(files),
            output_dir=output_dir,
            empty_output_folder=empty_output_folder,
            insert_end_mark=insert_end_mark,
            pdf_mode=pdf_mode,
        )
        run_conversion(snapshot, self.messages.put)

    def _poll_messages(self):
        try:
            while True:
                msg = self.messages.get_nowait()
                if msg[0] == "log":
                    self._append_log(msg[1], msg[2])
                elif msg[0] == "progress":
                    _, done, total, name = msg
                    self.progress.configure(value=done)
                    if done < total:
                        self.status.set(f"변환 중: {name}  ({done + 1}/{total})")
                elif msg[0] == "done":
                    self._finish_conversion(msg[1], msg[2])
        except queue.Empty:
            pass
        self.after(100, self._poll_messages)

    def _finish_conversion(self, completed, failures):
        finish_conversion(self, completed, failures)

    def _refresh_file_list(self):
        self.file_list.delete(0, tk.END)
        for item in self.files:
            self.file_list.insert(tk.END, f"  {Path(item).name}")
        self.count_text.set(f"{len(self.files)}개")

    def _append_log(self, text, tag=None):
        self.log.configure(state="normal")
        if tag:
            self.log.insert(tk.END, text + "\n", tag)
        else:
            self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)
        self.log.configure(state="disabled")


def main():
    app = ConverterApp()
    app.mainloop()


if __name__ == "__main__":
    main()
