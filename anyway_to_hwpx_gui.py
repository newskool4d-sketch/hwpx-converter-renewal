from pathlib import Path
import os
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

# ─── 시각 규칙 (DESIGN.md: 크림 배경 · muted blue 강조 · 1px 테두리) ──────────
BG = "#f7f4ee"          # 크림 배경
CARD = "#ffffff"        # 카드 배경
BORDER = "#e2ddd3"      # 연한 테두리
ACCENT = "#4a6fa5"      # muted blue
ACCENT_DARK = "#3d5d8a"
ACCENT_DIM = "#a8b6c9"
TEXT = "#1a1a1a"
MUTED = "#6b6b6b"
GREEN = "#4e7d5b"       # soft green (성공)
RED = "#a9504a"         # muted red (실패)
TROUGH = "#e8e4db"
LOG_BG = "#fbfaf7"

FONT = ("맑은 고딕", 10)
FONT_BOLD = ("맑은 고딕", 10, "bold")
FONT_SMALL = ("맑은 고딕", 9)
FONT_TITLE = ("맑은 고딕", 15, "bold")


class ConverterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HWPX 변환기")
        self.geometry("800x680")
        self.minsize(700, 560)
        self.configure(bg=BG)

        self.files = []
        self.output_dir = tk.StringVar()
        self.empty_output_folder = tk.BooleanVar(value=False)
        self.insert_end_mark = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="파일을 선택하세요.")
        self.count_text = tk.StringVar(value="0개")
        self.messages = queue.Queue()
        self.worker = None

        self._init_styles()
        self._build_ui()
        self.after(100, self._poll_messages)

    # ─── 스타일 ──────────────────────────────────────────────────────────────
    def _init_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=TEXT, font=FONT)

        style.configure("Card.TFrame", background=CARD)
        style.configure("Bg.TFrame", background=BG)

        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=FONT_TITLE)
        style.configure("Sub.TLabel", background=BG, foreground=MUTED, font=FONT_SMALL)
        style.configure("CardHead.TLabel", background=CARD, foreground=TEXT, font=FONT_BOLD)
        style.configure("CardMuted.TLabel", background=CARD, foreground=MUTED, font=FONT_SMALL)
        style.configure("Status.TLabel", background=BG, foreground=MUTED, font=FONT)

        style.configure(
            "Primary.TButton",
            background=ACCENT, foreground="#ffffff",
            font=FONT_BOLD, padding=(20, 9), borderwidth=0, focuscolor=ACCENT,
        )
        style.map(
            "Primary.TButton",
            background=[("disabled", ACCENT_DIM), ("active", ACCENT_DARK), ("pressed", ACCENT_DARK)],
        )
        style.configure(
            "Secondary.TButton",
            background=CARD, foreground=TEXT,
            font=FONT, padding=(12, 6), borderwidth=1,
            bordercolor=BORDER, focuscolor=CARD, relief="solid",
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#f1ede5"), ("pressed", "#eae5db")],
            bordercolor=[("active", ACCENT)],
        )

        style.configure(
            "TCheckbutton",
            background=CARD, foreground=TEXT, font=FONT, focuscolor=CARD,
        )
        style.map("TCheckbutton", background=[("active", CARD)])

        style.configure(
            "Accent.Horizontal.TProgressbar",
            background=ACCENT, troughcolor=TROUGH, borderwidth=0, thickness=8,
        )

        style.configure(
            "Vertical.TScrollbar",
            background=BORDER, troughcolor=CARD, borderwidth=0, arrowsize=12,
        )

    def _card(self, parent):
        """1px 테두리 카드 프레임 (그림자 대신 테두리 사용)."""
        return tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1, bd=0)

    # ─── UI 구성 ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = ttk.Frame(self, style="Bg.TFrame", padding=(18, 14, 18, 12))
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=3)
        root.rowconfigure(6, weight=2)

        # 헤더
        header = ttk.Frame(root, style="Bg.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(header, text="HWPX 변환기", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="md · txt · docx · html · csv · xlsx · pdf  →  한글 HWPX",
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        # 카드 ① 파일 목록
        file_card = self._card(root)
        file_card.grid(row=1, column=0, rowspan=2, sticky="nsew")
        file_card.columnconfigure(0, weight=1)
        file_card.rowconfigure(1, weight=1)

        file_head = tk.Frame(file_card, bg=CARD)
        file_head.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 8))
        ttk.Label(file_head, text="변환할 파일", style="CardHead.TLabel").pack(side=tk.LEFT)
        ttk.Label(file_head, textvariable=self.count_text, style="CardMuted.TLabel").pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(file_head, text="목록 비우기", style="Secondary.TButton", command=self.clear_files).pack(side=tk.RIGHT)
        ttk.Button(file_head, text="선택 삭제", style="Secondary.TButton", command=self._remove_selected).pack(side=tk.RIGHT, padx=(0, 6))
        ttk.Button(file_head, text="파일 추가", style="Secondary.TButton", command=self.select_files).pack(side=tk.RIGHT, padx=(0, 6))

        list_wrap = tk.Frame(file_card, bg=CARD)
        list_wrap.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 12))
        list_wrap.columnconfigure(0, weight=1)
        list_wrap.rowconfigure(0, weight=1)

        self.file_list = tk.Listbox(
            list_wrap, height=9, activestyle="none", selectmode=tk.EXTENDED,
            bg=LOG_BG, fg=TEXT, font=FONT,
            selectbackground=ACCENT, selectforeground="#ffffff",
            relief="flat", highlightthickness=1, highlightbackground=BORDER,
            highlightcolor=ACCENT,
        )
        self.file_list.grid(row=0, column=0, sticky="nsew")
        self.file_list.bind("<Delete>", lambda e: self._remove_selected())
        self.file_list.bind("<BackSpace>", lambda e: self._remove_selected())

        list_scroll = ttk.Scrollbar(list_wrap, orient="vertical", command=self.file_list.yview)
        list_scroll.grid(row=0, column=1, sticky="ns", padx=(4, 0))
        self.file_list.configure(yscrollcommand=list_scroll.set)

        # 카드 ② 저장 설정
        out_card = self._card(root)
        out_card.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        out_card.columnconfigure(1, weight=1)

        ttk.Label(out_card, text="저장 설정", style="CardHead.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", padx=14, pady=(12, 8)
        )
        tk.Label(out_card, text="저장 폴더", bg=CARD, fg=MUTED, font=FONT).grid(
            row=1, column=0, sticky="w", padx=(14, 8)
        )
        self.out_entry = tk.Entry(
            out_card, textvariable=self.output_dir,
            bg=LOG_BG, fg=TEXT, font=FONT, relief="flat",
            highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT,
        )
        self.out_entry.grid(row=1, column=1, sticky="ew", ipady=5)
        ttk.Button(out_card, text="찾기", style="Secondary.TButton", command=self.select_output_dir).grid(
            row=1, column=2, padx=(8, 14)
        )

        opts = tk.Frame(out_card, bg=CARD)
        opts.grid(row=2, column=0, columnspan=3, sticky="ew", padx=14, pady=(10, 12))
        ttk.Checkbutton(
            opts, text="저장 폴더 비우기(앱 관리 파일만)", variable=self.empty_output_folder,
        ).pack(side=tk.LEFT, padx=(0, 18))
        ttk.Checkbutton(
            opts, text="문서 끝에 '끝' 자동 삽입 (공문서)", variable=self.insert_end_mark,
        ).pack(side=tk.LEFT)

        # 실행 영역
        action = ttk.Frame(root, style="Bg.TFrame")
        action.grid(row=4, column=0, sticky="ew", pady=(14, 0))
        action.columnconfigure(0, weight=1)

        self.progress = ttk.Progressbar(action, mode="determinate", style="Accent.Horizontal.TProgressbar")
        self.progress.grid(row=0, column=0, sticky="ew", padx=(0, 14))
        self.convert_button = ttk.Button(action, text="변환 시작", style="Primary.TButton", command=self.start_conversion)
        self.convert_button.grid(row=0, column=1)

        ttk.Label(root, textvariable=self.status, style="Status.TLabel").grid(
            row=5, column=0, sticky="w", pady=(8, 6)
        )

        # 카드 ③ 로그
        log_card = self._card(root)
        log_card.grid(row=6, column=0, sticky="nsew")
        log_card.columnconfigure(0, weight=1)
        log_card.rowconfigure(1, weight=1)

        ttk.Label(log_card, text="진행 로그", style="CardHead.TLabel").grid(
            row=0, column=0, sticky="w", padx=14, pady=(10, 6)
        )
        log_wrap = tk.Frame(log_card, bg=CARD)
        log_wrap.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 12))
        log_wrap.columnconfigure(0, weight=1)
        log_wrap.rowconfigure(0, weight=1)

        self.log = tk.Text(
            log_wrap, height=7, wrap="word", state="disabled",
            bg=LOG_BG, fg=TEXT, font=FONT_SMALL, relief="flat",
            highlightthickness=1, highlightbackground=BORDER,
            padx=8, pady=6, spacing1=2,
        )
        self.log.grid(row=0, column=0, sticky="nsew")
        self.log.tag_configure("ok", foreground=GREEN)
        self.log.tag_configure("err", foreground=RED)
        self.log.tag_configure("muted", foreground=MUTED)

        log_scroll = ttk.Scrollbar(log_wrap, orient="vertical", command=self.log.yview)
        log_scroll.grid(row=0, column=1, sticky="ns", padx=(4, 0))
        self.log.configure(yscrollcommand=log_scroll.set)

    # ─── 동작 ────────────────────────────────────────────────────────────────
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

    def _remove_selected(self):
        if self.worker and self.worker.is_alive():
            return
        indices = sorted(self.file_list.curselection(), reverse=True)
        for idx in indices:
            del self.files[idx]
        self._refresh_file_list()
        count = len(self.files)
        self.status.set(f"{count}개 파일 선택됨" if count else "파일을 선택하세요.")

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
        if self.empty_output_folder.get():
            confirmed = messagebox.askyesno(
                "저장 폴더 비우기",
                "앱 manifest가 관리하는 기존 출력 파일만 삭제한 뒤 변환합니다.\n계속할까요?",
            )
            if not confirmed:
                return

        self.convert_button.configure(state="disabled")
        self.progress.configure(maximum=len(self.files), value=0)
        self.status.set("HWP 실행 중...")
        self._append_log("HWP 실행 중...", "muted")
        self.worker = threading.Thread(target=self._convert_worker, daemon=True)
        self.worker.start()

    def _convert_worker(self):
        pythoncom.CoInitialize()
        hwp = None
        failures = []
        completed = 0
        total = len(self.files)
        try:
            prepared_output_dir = converter.prepare_output_dir(
                self.output_dir.get(),
                empty_output_folder=self.empty_output_folder.get(),
            )
            hwp = converter.create_hwp_object(visible=True)
            time.sleep(1.5)

            for src in self.files:
                try:
                    src_path = converter.as_path(src)
                    out_path = converter.build_output_path(src_path, prepared_output_dir)
                    self.messages.put(("progress", completed, total, src_path.name))
                    self.messages.put(("log", f"변환 중: {src_path.name} → {out_path.name}", None))
                    converter.convert_file(
                        hwp,
                        src_path,
                        out_path,
                        insert_end_mark=self.insert_end_mark.get(),
                        kordoc_home=None,
                    )
                    converter.record_output_file(prepared_output_dir, out_path)
                    completed += 1
                    self.messages.put(("progress", completed, total, src_path.name))
                    self.messages.put(("log", f"완료: {out_path.name}", "ok"))
                except Exception as exc:
                    failures.append((src, exc))
                    self.messages.put(("log", f"실패: {Path(src).name} — {exc}", "err"))
        except Exception as exc:
            failures.append(("HWP 실행", exc))
            self.messages.put(("log", traceback.format_exc(), "err"))
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
        self.progress.configure(value=completed)
        self.convert_button.configure(state="normal")
        if failures:
            self.status.set(f"완료 {completed}개 · 실패 {len(failures)}개")
            lines = [
                f"• {Path(t).name if t != 'HWP 실행' else t}: {e}"
                for t, e in failures[:5]
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
            self.status.set(f"전체 변환 완료: {completed}개")
            open_folder = messagebox.askyesno(
                "변환 완료",
                f"{completed}개 파일을 변환했습니다.\n저장 폴더를 열까요?",
            )
            if open_folder:
                out_dir = self.output_dir.get().strip()
                if out_dir and os.path.isdir(out_dir):
                    os.startfile(out_dir)

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
