"""Optional document tools. Imported only when the user opens the workbench."""
from __future__ import annotations

import base64
import hashlib
import html
import json
from pathlib import Path
import queue
import secrets
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser
import xml.etree.ElementTree as ET


DOCUMENT_TYPES = (("한글 문서", "*.hwpx *.hwp"), ("모든 파일", "*.*"))
ACTION_LABELS = {
    "parse": "본문·표 읽기", "compare": "두 문서 비교", "validate": "구조 검사",
    "fields": "양식 항목 찾기", "fill": "양식 채우기", "patch": "본문 수정",
    "render": "페이지 미리보기", "profile": "견본 서식 추출", "lint": "공문 표기 점검",
    "diagnose": "도구 연결 확인",
}
STATUS_LABELS = {"success": "완료", "partial": "일부 완료 · 확인 필요", "error": "실패", "cancelled": "취소됨"}


def input_fingerprints(paths):
    """Bind an edit preview to the exact source/value files the user reviewed."""
    return {str(Path(p).resolve()): hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}


def safe_preview_html(svg: str, title: str = "문서 미리보기") -> str:
    """Render untrusted SVG as an isolated image, never as active browser markup."""
    if len(svg) > 32 * 1024 * 1024:
        raise ValueError("미리보기 크기가 제한을 초과했습니다.")
    if "<!DOCTYPE" in svg.upper() or "<!ENTITY" in svg.upper():
        raise ValueError("외부 정의가 있는 SVG는 열 수 없습니다.")
    root = ET.fromstring(svg)
    if root.tag.rsplit("}", 1)[-1].lower() != "svg":
        raise ValueError("SVG 미리보기 형식이 아닙니다.")
    banned = {"script", "foreignobject", "iframe", "object", "embed", "audio", "video"}
    for parent in list(root.iter()):
        for child in list(parent):
            if child.tag.rsplit("}", 1)[-1].lower() in banned:
                parent.remove(child)
            elif child.tag.rsplit("}", 1)[-1].lower() == "style" and any(
                token in (child.text or "").lower() for token in ("@import", "url(", "\\")
            ):
                parent.remove(child)
        for key, value in list(parent.attrib.items()):
            local = key.rsplit("}", 1)[-1].lower()
            if local.startswith("on") or (local == "href" and not value.startswith(("#", "data:image/png;base64,", "data:image/jpeg;base64,"))):
                del parent.attrib[key]
            elif "url(" in value.lower() and "url(#" not in value.lower():
                del parent.attrib[key]
    encoded = base64.b64encode(ET.tostring(root, encoding="utf-8")).decode("ascii")
    nonce = secrets.token_hex(16)
    return f'''<!doctype html><html lang="ko"><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'nonce-{nonce}'; base-uri 'none'; form-action 'none'">
<title>{html.escape(title)}</title><style>body{{margin:0;background:#e8edf2;color:#182334;font:15px sans-serif}}header{{position:sticky;top:0;padding:14px;background:white;border-bottom:1px solid #ccc}}img{{display:block;margin:20px auto;box-shadow:0 2px 15px #aaa;background:white}}button{{padding:6px 14px;margin:0 4px}}</style>
<header><strong>{html.escape(title)}</strong> · 검토용 미리보기 · 한컴 화면/인쇄와 다를 수 있습니다.
<button id="smaller">축소</button><span id="zoom">100%</span><button id="larger">확대</button></header>
<img id="page" alt="문서 페이지" src="data:image/svg+xml;base64,{encoded}">
<script nonce="{nonce}">let scale=100;const page=document.getElementById('page');let width=0;page.onload=()=>{{width=page.naturalWidth;page.style.width=width+'px'}};function zoom(delta){{scale=Math.max(25,Math.min(300,scale+delta));page.style.width=(width*scale/100)+'px';document.getElementById('zoom').textContent=scale+'%'}}document.getElementById('smaller').onclick=()=>zoom(-25);document.getElementById('larger').onclick=()=>zoom(25);</script></html>'''


def result_text(result: dict) -> str:
    """Keep partial/error status prominent even if there is useful result data."""
    lines = [STATUS_LABELS.get(result.get("status"), "확인 필요")]
    error = result.get("error")
    if error:
        lines.append(str(error.get("message", error) if isinstance(error, dict) else error))
    for warning in result.get("warnings") or []:
        lines.append("확인 필요: " + (warning if isinstance(warning, str) else json.dumps(warning, ensure_ascii=False)))
    data = result.get("data") or {}
    if isinstance(data, dict) and result.get("action") == "parse":
        lines.extend(["", str(data.get("markdown", "")), "", "구조 정보", json.dumps({k: v for k, v in data.items() if k != "markdown"}, ensure_ascii=False, indent=2)])
    else:
        visible = {k: v for k, v in data.items() if k != "svg"} if isinstance(data, dict) else data
        lines.extend(["", json.dumps(visible, ensure_ascii=False, indent=2)])
    return "\n".join(lines)


def change_entries(diffs):
    """Map actual kordoc BlockDiff order to source/result blocks and cell locations."""
    entries = []
    before_index = after_index = 0
    names = {"added": "추가", "removed": "삭제", "modified": "수정"}
    for diff in diffs if isinstance(diffs, list) else []:
        if not isinstance(diff, dict):
            continue
        kind = diff.get("type", "modified")
        if kind != "added":
            before_index += 1
        if kind != "removed":
            after_index += 1
        if kind == "unchanged":
            continue
        positions = []
        if kind != "added":
            positions.append(f"원본 {before_index}번")
        if kind != "removed":
            positions.append(f"수정 {after_index}번")
        block = diff.get("after") or diff.get("before") or {}
        if not isinstance(block, dict):
            block = {}
        block_type = {"heading": "제목", "table": "표", "image": "그림"}.get(block.get("type"), "문단")
        location = " → ".join(positions) + f" {block_type}"
        if block.get("pageNumber"):
            location += f" ({block['pageNumber']}쪽)"
        entries.append((location, names.get(kind, kind), diff))
        for row_index, row in enumerate(diff.get("cellDiffs") or []):
            for col_index, cell in enumerate(row):
                if isinstance(cell, dict) and cell.get("type") != "unchanged":
                    cell_location = f"{location} · {row_index + 1}행 {col_index + 1}열"
                    entries.append((cell_location, names.get(cell.get("type"), "셀 변경"), cell))
    return entries


class DocumentWorkbench(tk.Toplevel):
    def __init__(self, master, *, client=None):
        super().__init__(master)
        self.title("문서 읽기 · 비교 · 수정")
        self.geometry("1000x740")
        self.minsize(820, 600)
        self.source = tk.StringVar()
        self.other = tk.StringVar()
        self.page = tk.StringVar(value="1")
        self.page_count = 1
        self.status = tk.StringVar(value="한글 문서를 선택하고 작업을 누르세요.")
        self.messages = queue.Queue()
        self.cancel_event = threading.Event()
        self.worker = None
        self.client = client
        self.result = None
        self.edit_preview = None
        self._closed = False
        self._closing = False
        self._preview_files = None
        self._controls = []
        self._diffs = []
        self._input_paths = set()
        self._build()
        self.source.trace_add("write", self._invalidate_edit)
        self.other.trace_add("write", self._invalidate_edit)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self._poll_id = self.after(100, self._poll)

    def _button(self, frame, label, command, **pack):
        button = ttk.Button(frame, text=label, command=command)
        button.pack(side=tk.LEFT, padx=(0, 5), **pack)
        self._controls.append(button)
        return button

    def _build(self):
        body = ttk.Frame(self, padding=14)
        body.pack(fill=tk.BOTH, expand=True)
        for label, variable in (("기준 문서", self.source), ("비교 문서", self.other)):
            row = ttk.Frame(body)
            row.pack(fill=tk.X, pady=(0, 7))
            ttk.Label(row, text=label, width=10).pack(side=tk.LEFT)
            entry = ttk.Entry(row, textvariable=variable)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
            self._controls.append(entry)
            self._button(row, "파일 선택", lambda v=variable: self._choose(v))
        ttk.Label(body, text="본문 수정은 읽은 내용을 Markdown으로 저장한 뒤 편집하여 불러옵니다. 양식 값은 JSON 파일로 불러옵니다.").pack(anchor="w", pady=(0, 8))
        for actions in (("parse", "compare", "validate", "fields", "lint"), ("fill", "patch", "profile", "diagnose")):
            row = ttk.Frame(body)
            row.pack(fill=tk.X, pady=(0, 7))
            for action in actions:
                self._button(row, ACTION_LABELS[action], lambda a=action: self.run_action(a))
        preview = ttk.Frame(body)
        preview.pack(fill=tk.X, pady=(0, 7))
        self._button(preview, "이전 페이지", lambda: self._change_page(-1))
        self.page_entry = ttk.Entry(preview, textvariable=self.page, width=6)
        self.page_entry.pack(side=tk.LEFT, padx=(0, 5))
        self._controls.append(self.page_entry)
        self._button(preview, "페이지 미리보기", lambda: self.run_action("render"))
        self._button(preview, "다음 페이지", lambda: self._change_page(1))
        ttk.Label(preview, text="브라우저에서 확대·축소 가능 · 한컴 화면/인쇄 확인은 별도").pack(side=tk.LEFT, padx=8)
        ttk.Label(body, textvariable=self.status, wraplength=930).pack(anchor="w", pady=(3, 8))
        notebook = ttk.Notebook(body)
        notebook.pack(fill=tk.BOTH, expand=True)
        result_frame = ttk.Frame(notebook)
        notebook.add(result_frame, text="결과 · 경고")
        self.result_box = tk.Text(result_frame, wrap="word", state="disabled", font=("맑은 고딕", 10))
        self.result_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(result_frame, command=self.result_box.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_box.configure(yscrollcommand=scroll.set)
        changes_frame = ttk.Frame(notebook)
        notebook.add(changes_frame, text="변경 위치")
        self.changes = ttk.Treeview(changes_frame, columns=("location", "kind"), show="headings", height=6)
        self.changes.heading("location", text="문단 · 표 셀 위치")
        self.changes.heading("kind", text="변경 내용")
        self.changes.column("location", width=210)
        self.changes.column("kind", width=640)
        self.changes.pack(fill=tk.BOTH, expand=True)
        self.changes.bind("<<TreeviewSelect>>", self._select_change)
        self.change_detail = tk.Text(changes_frame, height=8, state="disabled", wrap="word", font=("맑은 고딕", 10))
        self.change_detail.pack(fill=tk.BOTH, expand=True)
        footer = ttk.Frame(body)
        footer.pack(fill=tk.X, pady=(9, 0))
        self.save_report_button = self._button(footer, "보고서 저장(JSON)", self.save_report)
        self.save_markdown_button = self._button(footer, "본문 저장(MD)", self.save_markdown)
        self.apply_button = self._button(footer, "검토한 수정본 저장", self.apply_edit)
        self.cancel_button = ttk.Button(footer, text="작업 취소", command=self.cancel_event.set, state="disabled")
        self.cancel_button.pack(side=tk.RIGHT)
        self._set_busy(False)

    def _choose(self, variable):
        selected = filedialog.askopenfilename(parent=self, title="한글 문서 선택", filetypes=DOCUMENT_TYPES)
        if selected:
            variable.set(selected)
            self.edit_preview = None
            self._set_busy(False)

    def _invalidate_edit(self, *_args):
        self.edit_preview = None
        self.apply_button.configure(state="disabled")

    def _set_busy(self, busy):
        for control in self._controls:
            control.configure(state="disabled" if busy else "normal")
        self.cancel_button.configure(state="normal" if busy else "disabled")
        if not busy:
            self.save_report_button.configure(state="normal" if self.result else "disabled")
            markdown = (self.result or {}).get("data") or {}
            self.save_markdown_button.configure(state="normal" if isinstance(markdown, dict) and markdown.get("markdown") else "disabled")
            self.apply_button.configure(state="normal" if self.edit_preview else "disabled")

    def _busy(self):
        return self.worker is not None and self.worker.is_alive()

    def run_action(self, action):
        if self._busy():
            return
        params = {}
        if action != "diagnose":
            source = self.source.get().strip()
            if not source or not Path(source).is_file():
                messagebox.showwarning("확인", "기준 문서를 선택하세요.", parent=self)
                return
            params["path"] = source
        if action == "compare":
            other = self.other.get().strip()
            if not other or not Path(other).is_file():
                messagebox.showwarning("확인", "비교 문서를 선택하세요.", parent=self)
                return
            params = {"before": source, "after": other}
        elif action in ("fill", "patch"):
            filetypes = (("양식 값 JSON", "*.json"),) if action == "fill" else (("수정한 Markdown", "*.md"),)
            extra = filedialog.askopenfilename(parent=self, title="양식 값 선택" if action == "fill" else "수정한 본문 선택", filetypes=filetypes)
            if not extra:
                return
            params["values_file" if action == "fill" else "markdown_file"] = extra
            params["dry_run"] = True
        elif action == "render":
            try:
                page = int(self.page.get())
                if page < 1:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("확인", "페이지는 1 이상의 숫자로 입력하세요.", parent=self)
                return
            params["page"] = page
        self._start(action, params)

    def _start(self, action, params):
        self.edit_preview = None
        self.cancel_event = threading.Event()
        self._set_busy(True)
        self.status.set(f"{ACTION_LABELS[action]} 진행 중…")
        self._input_paths = {str(Path(value).resolve()) for key, value in params.items()
                             if key in ("path", "before", "after", "values_file", "markdown_file")}
        # Worker uses plain Python data; all Tk calls stay on the UI thread.
        def work():
            fingerprints = None
            try:
                if self.client is None:
                    from kordoc_client import KordocClient
                    self.client = KordocClient()
                if action in ("fill", "patch") and params.get("dry_run"):
                    fingerprints = input_fingerprints([params["path"], params.get("values_file") or params["markdown_file"]])
                result = self.client.request(action, cancel_event=self.cancel_event, **params)
            except Exception as exc:
                result = {"ok": False, "status": "error", "action": action, "data": {}, "warnings": [], "error": {"code": "client_error", "message": str(exc)}}
            self.messages.put((result, params, fingerprints))
        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def _poll(self):
        if self._closed:
            return
        try:
            while True:
                result, params, fingerprints = self.messages.get_nowait()
                self._show_result(result, params, fingerprints)
        except queue.Empty:
            pass
        if self._closing and not self._busy():
            self.close()
            return
        self._poll_id = self.after(100, self._poll)

    @staticmethod
    def _write_text(widget, text):
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _show_result(self, result, params, fingerprints):
        self.result = result
        action = result.get("action", "")
        state = result.get("status", "error")
        self.status.set(f"{ACTION_LABELS.get(action, action)} · {STATUS_LABELS.get(state, state)}")
        rendered = result_text(result)
        if len(rendered) > 200000:
            rendered = rendered[:200000] + "\n\n화면에는 일부만 표시합니다. 전체 내용은 보고서로 저장하세요."
        self._write_text(self.result_box, rendered)
        self.changes.delete(*self.changes.get_children())
        self._write_text(self.change_detail, "변경 항목을 선택하면 자세한 내용을 볼 수 있습니다.")
        data = result.get("data") or {}
        raw_diffs = data.get("diffs", (data.get("changes") or {}).get("diffs", [])) if isinstance(data, dict) else []
        entries = change_entries(raw_diffs)
        self._diffs = [entry[2] for entry in entries[:1000]]
        for index, (location, kind, _diff) in enumerate(entries[:1000]):
            self.changes.insert("", "end", iid=str(index), values=(location, kind))
        if len(entries) > 1000:
            self._write_text(self.change_detail, f"변경 {len(entries)}건 중 앞의 1,000건을 표시합니다. 전체 변경은 보고서로 저장하세요.")
        if fingerprints and state == "success":
            self.edit_preview = (action, dict(params), fingerprints)
            self.status.set(self.status.get() + " · 결과를 검토한 뒤 수정본을 저장하세요.")
        elif fingerprints and state == "partial":
            self.status.set(self.status.get() + " · 적용 불가 항목을 해결한 뒤 다시 확인하세요. 수정본은 저장하지 않았습니다.")
        self._set_busy(False)
        if action == "render" and state in ("success", "partial") and data.get("svg") and not self._closing:
            self.page_count = int(data.get("pageCount") or 1)
            self.page.set(str(data.get("page") or 1))
            self.status.set(self.status.get() + f" · {self.page.get()}/{self.page_count}쪽")
            try:
                preview = safe_preview_html(data["svg"], f"문서 미리보기 {self.page.get()}/{self.page_count}쪽")
                if self._preview_files is None:
                    self._preview_files = tempfile.TemporaryDirectory(prefix="hwpx-preview-")
                path = Path(self._preview_files.name) / f"page-{self.page.get()}.html"
                path.write_text(preview, encoding="utf-8")
                if not webbrowser.open(path.as_uri()):
                    messagebox.showinfo("미리보기", f"브라우저에서 이 파일을 여세요:\n{path}", parent=self)
            except (ValueError, OSError, ET.ParseError) as exc:
                self.status.set(f"미리보기를 열지 못했습니다: {exc}")

    def _select_change(self, _event=None):
        selected = self.changes.selection()
        if selected:
            self._write_text(self.change_detail, json.dumps(self._diffs[int(selected[0])], ensure_ascii=False, indent=2))

    def _change_page(self, delta):
        try:
            value = int(self.page.get()) + delta
        except ValueError:
            value = 1
        self.page.set(str(max(1, min(self.page_count, value))))
        self.run_action("render")

    def apply_edit(self):
        if self._busy() or not self.edit_preview:
            return
        action, params, fingerprints = self.edit_preview
        try:
            if input_fingerprints(fingerprints.keys()) != fingerprints:
                raise ValueError("미리보기 이후 입력 파일이 바뀌었습니다. 다시 미리보기를 실행하세요.")
        except (OSError, ValueError) as exc:
            self.edit_preview = None
            self._set_busy(False)
            messagebox.showwarning("다시 확인", str(exc), parent=self)
            return
        source = Path(params["path"])
        output = filedialog.asksaveasfilename(parent=self, title="원본과 다른 새 수정본 저장", initialfile=f"{source.stem}_수정{source.suffix}", defaultextension=source.suffix, filetypes=DOCUMENT_TYPES)
        if not output:
            return
        if Path(output).exists() or Path(output).resolve() == source.resolve():
            messagebox.showwarning("확인", "원본과 기존 파일은 덮어쓰지 않습니다. 새 파일명을 선택하세요.", parent=self)
            return
        try:
            if input_fingerprints(fingerprints.keys()) != fingerprints:
                raise ValueError("저장 위치를 선택하는 동안 입력이 바뀌었습니다. 다시 미리보기를 실행하세요.")
        except (OSError, ValueError) as exc:
            self.edit_preview = None
            self._set_busy(False)
            messagebox.showwarning("다시 확인", str(exc), parent=self)
            return
        params = dict(params, output=output, dry_run=False, expected_fingerprints=fingerprints)
        self._start(action, params)

    def save_report(self):
        if not self.result:
            return
        output = filedialog.asksaveasfilename(parent=self, title="결과 보고서 저장 (본문 정보 포함)", defaultextension=".json", filetypes=(("JSON 보고서", "*.json"),))
        if output:
            try:
                self._validate_export_path(output, ".json")
                Path(output).write_text(json.dumps(self.result, ensure_ascii=False, indent=2), encoding="utf-8")
                self.status.set("보고서를 저장했습니다.")
            except (OSError, ValueError) as exc:
                messagebox.showerror("저장 실패", str(exc), parent=self)

    def save_markdown(self):
        markdown = ((self.result or {}).get("data") or {}).get("markdown")
        if not markdown:
            return
        output = filedialog.asksaveasfilename(parent=self, title="본문 저장", defaultextension=".md", filetypes=(("Markdown", "*.md"),))
        if output:
            try:
                self._validate_export_path(output, ".md")
                Path(output).write_text(markdown, encoding="utf-8")
                self.status.set("본문을 저장했습니다. 편집 후 '본문 수정'으로 불러오세요.")
            except (OSError, ValueError) as exc:
                messagebox.showerror("저장 실패", str(exc), parent=self)

    def _validate_export_path(self, output, extension):
        path = Path(output).resolve()
        protected = self._input_paths | {str(Path(value.get()).resolve()) for value in (self.source, self.other) if value.get().strip()}
        if str(path) in protected or path.suffix.lower() != extension:
            raise ValueError(f"입력 원본은 덮어쓰지 않습니다. {extension} 형식의 다른 파일을 선택하세요.")

    def close(self):
        if self._busy():
            self._closing = True
            self.cancel_event.set()
            self.status.set("작업을 취소하고 창을 닫는 중…")
            return
        self._closed = True
        self.after_cancel(self._poll_id)
        if self._preview_files is not None:
            self._preview_files.cleanup()
        self.destroy()
