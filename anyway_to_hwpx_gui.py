"""
GUI wrapper for anyway_to_hwpx_com.py.

Flow:
1. Select one or more source files.
2. Select an output folder.
3. Convert files to HWPX through the existing HWP COM converter.
"""
from pathlib import Path
import queue
import threading
import time
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import pythoncom

import anyway_to_hwpx_com as converter


SUPPORTED_PATTERNS = [
    ("Supported files", "*.md *.txt *.docx *.html *.htm *.csv *.xlsx *.pdf"),
    ("Markdown", "*.md"),
    ("Text", "*.txt"),
    ("Word", "*.docx"),
    ("HTML", "*.html *.htm"),
    ("Spreadsheet", "*.csv *.xlsx"),
    ("PDF", "*.pdf"),
    ("All files", "*.*"),
]


class ConverterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HWPX 변환기")
        self.geometry("760x520")
        self.minsize(680, 440)

        self.files = []
        self.output_dir = tk.StringVar()
        self.insert_end_mark = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="파일을 선택하세요.")
        self.messages = queue.Queue()
        self.worker = None

        self._build_ui()
        self.after(100, self._poll_messages)

    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        top = ttk.Frame(root)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Button(top, text="파일 선택", command=self.select_files).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(top, text="목록 비우기", command=self.clear_files).grid(row=0, column=1, sticky="w")

        self.file_list = tk.Listbox(root, height=10, activestyle="none")
        self.file_list.grid(row=1, column=0, sticky="nsew", pady=(10, 10))

        out = ttk.Frame(root)
        out.grid(row=2, column=0, sticky="ew")
        out.columnconfigure(1, weight=1)
        ttk.Label(out, text="저장 폴더").grid(row=0, column=0, padx=(0, 8))
        ttk.Entry(out, textvariable=self.output_dir).grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ttk.Button(out, text="찾기", command=self.select_output_dir).grid(row=0, column=2)

        options = ttk.Frame(root)
        options.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        ttk.Checkbutton(
            options,
            text="문서 끝에 '끝' 자동 삽입",
            variable=self.insert_end_mark,
        ).pack(side=tk.LEFT)

        actions = ttk.Frame(root)
        actions.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        actions.columnconfigure(0, weight=1)
        self.convert_button = ttk.Button(actions, text="변환 시작", command=self.start_conversion)
        self.convert_button.grid(row=0, column=1)

        self.progress = ttk.Progressbar(root, mode="indeterminate")
        self.progress.grid(row=5, column=0, sticky="ew", pady=(10, 0))

        ttk.Label(root, textvariable=self.status).grid(row=6, column=0, sticky="w", pady=(8, 4))

        self.log = tk.Text(root, height=9, wrap="word", state="disabled")
        self.log.grid(row=7, column=0, sticky="nsew")
        root.rowconfigure(7, weight=1)

    def select_files(self):
        selected = filedialog.askopenfilenames(title="변환할 파일 선택", filetypes=SUPPORTED_PATTERNS)
        if not selected:
            return
        known = set(self.files)
        for item in selected:
            if item not in known:
                self.files.append(item)
                known.add(item)
        self._refresh_file_list()
        if not self.output_dir.get() and self.files:
            self.output_dir.set(str(Path(self.files[0]).parent))
        self.status.set(f"{len(self.files)}개 파일 선택됨")

    def clear_files(self):
        if self.worker and self.worker.is_alive():
            return
        self.files.clear()
        self._refresh_file_list()
        self.status.set("파일을 선택하세요.")

    def select_output_dir(self):
        selected = filedialog.askdirectory(title="저장 폴더 선택")
        if selected:
            self.output_dir.set(selected)

    def start_conversion(self):
        if self.worker and self.worker.is_alive():
            return
        if not self.files:
            messagebox.showwarning("확인", "변환할 파일을 선택하세요.")
            return
        if not self.output_dir.get().strip():
            messagebox.showwarning("확인", "저장 폴더를 선택하세요.")
            return

        self.convert_button.configure(state="disabled")
        self.progress.start(10)
        self.status.set("변환 중...")
        self._append_log("HWP 실행 중...")
        self.worker = threading.Thread(target=self._convert_worker, daemon=True)
        self.worker.start()

    def _convert_worker(self):
        pythoncom.CoInitialize()
        hwp = None
        failures = []
        completed = 0
        try:
            hwp = converter.create_hwp_object(visible=True)
            time.sleep(1.5)

            for src in self.files:
                try:
                    src_path = converter.as_path(src)
                    out_path = converter.build_output_path(src_path, self.output_dir.get())
                    self.messages.put(("log", f"변환 중: {src_path.name} -> {out_path.name}"))
                    converter.convert_file(
                        hwp,
                        src_path,
                        out_path,
                        insert_end_mark=self.insert_end_mark.get(),
                        kordoc_home=None,
                    )
                    completed += 1
                    self.messages.put(("log", f"완료: {out_path}"))
                except Exception as exc:
                    failures.append((src, exc))
                    self.messages.put(("log", f"실패: {src} - {exc}"))
        except Exception as exc:
            failures.append(("HWP 실행", exc))
            self.messages.put(("log", traceback.format_exc()))
        finally:
            if hwp is not None:
                try:
                    hwp.Quit()
                except Exception:
                    pass
            pythoncom.CoUninitialize()
            self.messages.put(("done", completed, failures))

    def _poll_messages(self):
        try:
            while True:
                msg = self.messages.get_nowait()
                if msg[0] == "log":
                    self._append_log(msg[1])
                elif msg[0] == "done":
                    self._finish_conversion(msg[1], msg[2])
        except queue.Empty:
            pass
        self.after(100, self._poll_messages)

    def _finish_conversion(self, completed, failures):
        self.progress.stop()
        self.convert_button.configure(state="normal")
        if failures:
            self.status.set(f"완료 {completed}개, 실패 {len(failures)}개")
            first_target, first_error = failures[0]
            messagebox.showerror(
                "변환 실패",
                f"완료 {completed}개, 실패 {len(failures)}개입니다.\n\n"
                f"첫 실패: {first_target}\n{first_error}\n\n"
                "자세한 내용은 로그를 확인하세요.",
            )
        else:
            self.status.set(f"전체 변환 완료: {completed}개")
            messagebox.showinfo("변환 완료", f"{completed}개 파일을 변환했습니다.")

    def _refresh_file_list(self):
        self.file_list.delete(0, tk.END)
        for item in self.files:
            self.file_list.insert(tk.END, item)

    def _append_log(self, text):
        self.log.configure(state="normal")
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)
        self.log.configure(state="disabled")


def main():
    app = ConverterApp()
    app.mainloop()


if __name__ == "__main__":
    main()
