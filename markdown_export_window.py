"""Batch HWP·HWPX·PDF → Markdown window. Imported only when the user opens it."""
from __future__ import annotations

from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from markdown_export import DEFAULT_TIMEOUT_SECONDS, MARKDOWN_INPUT_EXTENSIONS, convert_to_markdown

INPUT_TYPES = (("한글·PDF 문서", " ".join(f"*{ext}" for ext in sorted(MARKDOWN_INPUT_EXTENSIONS))), ("모든 파일", "*.*"))


def run_markdown_batch(files, output_dir, images, sink, cancel_event, client=None):
    """Convert files in order; sink receives ("log", text, tag), ("progress", done, total), ("done", counts)."""
    if client is None:
        from kordoc_client import KordocClient

        client = KordocClient(timeout=DEFAULT_TIMEOUT_SECONDS)
    counts = {"success": 0, "partial": 0, "error": 0, "cancelled": 0}
    total = len(files)
    for index, source in enumerate(files):
        name = Path(source).name
        if cancel_event.is_set():
            counts["cancelled"] += total - index
            sink(("log", f"취소되어 처리하지 않음: {total - index}개", "warn"))
            break
        sink(("progress", index, total))
        sink(("log", f"변환 중: {name}", None))
        result = convert_to_markdown(source, output_dir or None, images=images, client=client, cancel_event=cancel_event)
        status = result.get("status") if result.get("status") in counts else "error"
        counts[status] += 1
        data = result.get("data") or {}
        if status in ("success", "partial"):
            saved = Path(data.get("output", "")).name
            extra = f" · 그림 {len(data.get('images') or [])}개" if data.get("imageDir") else ""
            sink(("log", f"완료: {name} → {saved}{extra}", "ok"))
            for warning in result.get("warnings") or []:
                text = warning if isinstance(warning, str) else (warning.get("message") if isinstance(warning, dict) else str(warning))
                sink(("log", f"[확인 필요] {text}", "warn"))
        else:
            message = (result.get("error") or {}).get("message", "변환하지 못했습니다.")
            sink(("log", f"{'취소' if status == 'cancelled' else '실패'}: {name} — {message}", "err"))
        sink(("progress", index + 1, total))
    sink(("done", counts))
    return counts


class MarkdownExportWindow(tk.Toplevel):
    def __init__(self, master, *, client=None):
        super().__init__(master)
        self.title("한글·PDF → Markdown")
        self.geometry("720x560")
        self.minsize(600, 460)
        self.client = client
        self.files: list[str] = []
        self.output_dir = tk.StringVar()
        self.images = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="한글(HWP·HWPX) 또는 PDF 문서를 추가하세요. 한글 프로그램 없이 변환합니다.")
        self.messages = queue.Queue()
        self.cancel_event = threading.Event()
        self.worker = None
        self._closing = False
        self._build()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self._poll_id = self.after(100, self._poll)

    def _build(self):
        body = ttk.Frame(self, padding=14)
        body.pack(fill=tk.BOTH, expand=True)
        head = ttk.Frame(body)
        head.pack(fill=tk.X)
        ttk.Label(head, text="변환할 문서").pack(side=tk.LEFT)
        self.clear_button = ttk.Button(head, text="목록 비우기", command=self._clear)
        self.clear_button.pack(side=tk.RIGHT)
        self.remove_button = ttk.Button(head, text="선택 삭제", command=self._remove)
        self.remove_button.pack(side=tk.RIGHT, padx=(0, 5))
        self.add_button = ttk.Button(head, text="파일 추가", command=self._add)
        self.add_button.pack(side=tk.RIGHT, padx=(0, 5))
        self.file_list = tk.Listbox(body, height=7, selectmode=tk.EXTENDED)
        self.file_list.pack(fill=tk.BOTH, expand=True, pady=(6, 10))
        row = ttk.Frame(body)
        row.pack(fill=tk.X)
        ttk.Label(row, text="저장 폴더").pack(side=tk.LEFT)
        self.out_entry = ttk.Entry(row, textvariable=self.output_dir)
        self.out_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        self.browse_button = ttk.Button(row, text="찾기", command=self._browse)
        self.browse_button.pack(side=tk.LEFT)
        self.images_check = ttk.Checkbutton(body, text="그림을 별도 폴더(문서명_images)에 저장", variable=self.images)
        self.images_check.pack(anchor="w", pady=(8, 0))
        ttk.Label(body, text="스캔 PDF(글자층 없음)·문서보안(DRM)·암호 문서는 변환하지 않습니다. 결과는 원본과 대조하세요.").pack(anchor="w", pady=(4, 8))
        action = ttk.Frame(body)
        action.pack(fill=tk.X)
        self.progress = ttk.Progressbar(action, mode="determinate")
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.cancel_button = ttk.Button(action, text="취소", command=self.cancel_event_set, state="disabled")
        self.cancel_button.pack(side=tk.RIGHT)
        self.start_button = ttk.Button(action, text="Markdown으로 변환", command=self.start)
        self.start_button.pack(side=tk.RIGHT, padx=(0, 6))
        ttk.Label(body, textvariable=self.status, wraplength=680).pack(anchor="w", pady=(8, 6))
        self.log = tk.Text(body, height=8, state="disabled", wrap="word")
        self.log.pack(fill=tk.BOTH, expand=True)
        for tag, color in (("ok", "#1a7f37"), ("warn", "#9a6700"), ("err", "#cf222e")):
            self.log.tag_configure(tag, foreground=color)
        self._controls = (self.add_button, self.remove_button, self.clear_button, self.out_entry,
                          self.browse_button, self.images_check, self.start_button)

    def _busy(self):
        return self.worker is not None and self.worker.is_alive()

    def _set_busy(self, busy):
        for control in self._controls:
            control.configure(state="disabled" if busy else "normal")
        self.cancel_button.configure(state="normal" if busy else "disabled")

    def _refresh(self):
        self.file_list.delete(0, tk.END)
        for item in self.files:
            self.file_list.insert(tk.END, f"  {Path(item).name}")

    def add_paths(self, paths):
        skipped = 0
        for value in paths:
            path = Path(value).expanduser().resolve()
            if path.suffix.lower() not in MARKDOWN_INPUT_EXTENSIONS or not path.is_file():
                skipped += 1
            elif str(path) not in self.files:
                self.files.append(str(path))
        if self.files and not self.output_dir.get().strip():
            self.output_dir.set(str(Path(self.files[0]).parent))
        self._refresh()
        self.status.set(f"{len(self.files)}개 문서 선택됨" + (f" · 지원하지 않는 파일 {skipped}개 제외" if skipped else ""))

    def _add(self):
        selected = filedialog.askopenfilenames(parent=self, title="변환할 문서 선택", filetypes=INPUT_TYPES)
        if selected:
            self.add_paths(selected)

    def _remove(self):
        for index in sorted(self.file_list.curselection(), reverse=True):
            del self.files[index]
        self._refresh()

    def _clear(self):
        self.files.clear()
        self._refresh()

    def _browse(self):
        selected = filedialog.askdirectory(parent=self, title="저장 폴더 선택")
        if selected:
            self.output_dir.set(selected)

    def cancel_event_set(self):
        self.cancel_event.set()
        self.cancel_button.configure(state="disabled")
        self.status.set("취소 중… 현재 문서를 정리합니다.")

    def _write_log(self, text, tag=None):
        self.log.configure(state="normal")
        self.log.insert(tk.END, text + "\n", tag or ())
        self.log.see(tk.END)
        self.log.configure(state="disabled")

    def start(self):
        if self._busy():
            return
        if not self.files:
            messagebox.showwarning("확인", "변환할 문서를 추가하세요.", parent=self)
            return
        files, output_dir, images = tuple(self.files), self.output_dir.get().strip(), bool(self.images.get())
        self.cancel_event = threading.Event()
        cancel_event = self.cancel_event
        self._set_busy(True)
        self.progress.configure(maximum=len(files), value=0)
        self.status.set("변환 중…")

        def work():
            try:
                run_markdown_batch(files, output_dir, images, self.messages.put, cancel_event, client=self.client)
            except Exception as exc:  # noqa: BLE001 — surface any unexpected failure in the window
                self.messages.put(("log", f"실패: {exc}", "err"))
                self.messages.put(("done", {"success": 0, "partial": 0, "error": len(files), "cancelled": 0}))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def _poll(self):
        try:
            while True:
                message = self.messages.get_nowait()
                if message[0] == "log":
                    self._write_log(message[1], message[2])
                elif message[0] == "progress":
                    self.progress.configure(value=message[1])
                elif message[0] == "done":
                    counts = message[1]
                    self._set_busy(False)
                    self.status.set(
                        f"완료 {counts['success']}개 · 확인 필요 {counts['partial']}개 · 실패 {counts['error']}개"
                        + (f" · 취소 {counts['cancelled']}개" if counts["cancelled"] else ""))
        except queue.Empty:
            pass
        if self._closing and not self._busy():
            self.destroy()
            return
        self._poll_id = self.after(100, self._poll)

    def close(self):
        if self._busy():
            self._closing = True
            self.cancel_event_set()
            return
        self.after_cancel(self._poll_id)
        self.destroy()
