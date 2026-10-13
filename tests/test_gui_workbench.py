from __future__ import annotations

import base64
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import time
import tkinter as tk
import unittest
from unittest.mock import patch

from document_workbench import DocumentWorkbench, change_entries, input_fingerprints, result_text, safe_preview_html


def envelope(action, data=None, status="success", warnings=()):
    return {"ok": status == "success", "status": status, "action": action,
            "data": data or {}, "warnings": list(warnings), "error": None}


class PreviewSafetyTests(unittest.TestCase):
    def test_svg_cannot_execute_script_or_reference_external_resources(self):
        page = safe_preview_html('''<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)">
            <script>alert(2)</script><foreignObject><iframe src="https://example.com"/></foreignObject>
            <image href="https://example.com/a.png"/><text onclick="bad()">hello</text>
            <style>text { fill: blue; }</style></svg>''', "<bad>")
        self.assertIn("Content-Security-Policy", page)
        self.assertIn("&lt;bad&gt;", page)
        match = re.search(r'data:image/svg\+xml;base64,([A-Za-z0-9+/=]+)', page)
        svg = base64.b64decode(match.group(1)).decode("utf-8")
        for unsafe in ("script", "foreignObject", "onload", "onclick", "https://example.com"):
            self.assertNotIn(unsafe, svg)
        self.assertIn("fill: blue", svg)

    def test_external_entities_and_non_svg_are_rejected(self):
        for svg in ('<!DOCTYPE svg [<!ENTITY a "a">]><svg/>', "<html/>"):
            with self.assertRaises(ValueError):
                safe_preview_html(svg)

    def test_partial_status_and_warnings_remain_visible(self):
        text = result_text(envelope("patch", {"applied": 1, "skipped": 2}, "partial", ["병합 변경 미지원"]))
        self.assertIn("일부 완료", text)
        self.assertIn("병합 변경 미지원", text)
        self.assertIn('"skipped": 2', text)

    def test_preview_fingerprint_detects_source_change(self):
        with TemporaryDirectory() as temp:
            source = Path(temp) / "원본.hwpx"
            source.write_bytes(b"before")
            before = input_fingerprints([source])
            source.write_bytes(b"after")
            self.assertNotEqual(before, input_fingerprints([source]))

    def test_changes_after_thousand_unchanged_blocks_remain_visible_with_cell_coordinates(self):
        diffs = [{"type": "unchanged", "before": {"text": "same"}, "after": {"text": "same"}}] * 1001
        diffs += [{"type": "modified", "before": {"type": "table"}, "after": {"type": "table", "pageNumber": 25},
                   "cellDiffs": [[{"type": "unchanged"}, {"type": "modified", "before": "100", "after": "200"}]]}]
        entries = change_entries(diffs)
        self.assertEqual(len(entries), 2)
        self.assertIn("원본 1002번", entries[0][0])
        self.assertIn("25쪽", entries[0][0])
        self.assertIn("1행 2열", entries[1][0])

    def test_additions_and_removals_keep_separate_source_result_indices(self):
        entries = change_entries([{"type": "added", "after": {"text": "new"}},
                                  {"type": "removed", "before": {"text": "old"}},
                                  {"type": "modified", "before": {}, "after": {}}])
        self.assertIn("수정 1번", entries[0][0])
        self.assertNotIn("원본", entries[0][0])
        self.assertIn("원본 1번", entries[1][0])
        self.assertIn("원본 2번 → 수정 2번", entries[2][0])


class MainWindowRecoveryTests(unittest.TestCase):
    def test_optional_drop_library_failure_keeps_picker_and_busy_controls_working(self):
        import anyway_to_hwpx_gui as gui

        if gui.TkinterDnD is None:
            self.skipTest("끌어놓기 패키지 없음")
        with patch.object(gui.TkinterDnD, "_require", side_effect=RuntimeError("Unavailable")):
            app = gui.ConverterApp()
        try:
            app.withdraw()
            app.update_idletasks()
            self.assertFalse(app._dnd_available)
            self.assertEqual(str(app.add_button["state"]), "normal")
            app._set_busy(True)
            self.assertEqual(str(app.add_button["state"]), "disabled")
            self.assertEqual(str(app.cancel_button["state"]), "normal")
            app.failed_files = ["failed.md"]
            app._set_busy(False)
            self.assertEqual(str(app.retry_button["state"]), "normal")
            self.assertEqual(str(app.cancel_button["state"]), "disabled")
        finally:
            app.destroy()

    def test_retry_preserves_original_options_and_never_clears_completed_files(self):
        import anyway_to_hwpx_gui as gui

        app = gui.ConverterApp.__new__(gui.ConverterApp)
        app._is_busy = lambda: False
        app.failed_files = ["failed.md"]
        app._last_snapshot_args = (("success.md", "failed.md"), "output", True, True, "editable", True, "sihaengmun")
        launched = []
        app._launch_conversion = launched.append
        app.retry_failed()
        self.assertEqual(launched, [(("failed.md",), "output", False, True, "editable", True, "sihaengmun")])


class _Client:
    def __init__(self):
        self.calls = []
        self.partial = False
        self.wait_for_cancel = False

    def request(self, action, *, cancel_event=None, **kwargs):
        self.calls.append((action, kwargs))
        if self.wait_for_cancel:
            cancel_event.wait(2)
            return envelope(action, status="cancelled")
        if action == "parse":
            return envelope(action, {"markdown": "# 본문\n금액 100원", "blocks": []})
        if action == "compare":
            return envelope(action, {"diffs": [{"type": "modified", "before": {"text": "100"}, "after": {"text": "200"}}]})
        if action in ("patch", "fill"):
            if self.partial:
                return envelope(action, {"skipped": 1}, "partial", ["지원하지 않는 변경"])
            if not kwargs.get("dry_run"):
                Path(kwargs["output"]).write_bytes(b"modified-copy")
            return envelope(action, {"output": kwargs.get("output"), "applied": 1})
        if action == "render":
            return envelope(action, {"svg": '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><text>한글</text></svg>', "page": kwargs["page"], "pageCount": 2})
        return envelope(action)


class WorkbenchInteractionTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk 화면 없음: {exc}")
        self.root.withdraw()
        self.temp = TemporaryDirectory()
        self.source = Path(self.temp.name) / "원본.hwpx"
        self.other = Path(self.temp.name) / "비교.hwpx"
        self.markdown = Path(self.temp.name) / "본문.md"
        self.source.write_bytes(b"original")
        self.other.write_bytes(b"other")
        self.markdown.write_text("# 변경", encoding="utf-8")
        self.client = _Client()
        self.app = DocumentWorkbench(self.root, client=self.client)
        self.app.withdraw()
        self.app.source.set(str(self.source))
        self.app.other.set(str(self.other))

    def tearDown(self):
        if hasattr(self, "app"):
            self.app.cancel_event.set()
            if self.app.worker:
                self.app.worker.join(3)
            if self.app.winfo_exists():
                self.app.close()
            self.root.destroy()
            self.temp.cleanup()

    def complete(self):
        limit = time.monotonic() + 3
        while time.monotonic() < limit:
            self.root.update()
            if not self.app._busy() and self.app.result is not None and not self.app.messages.qsize():
                return
            time.sleep(0.01)
        self.fail("문서 작업 결과가 UI에 반영되지 않음")

    def test_read_compare_and_cancel_leave_window_responsive(self):
        self.app.run_action("parse")
        self.complete()
        self.assertIn("금액 100원", self.app.result_box.get("1.0", tk.END))
        self.assertEqual(str(self.app.save_markdown_button["state"]), "normal")
        self.app.run_action("compare")
        self.complete()
        self.app.changes.selection_set("0")
        self.app._select_change()
        self.assertIn("200", self.app.change_detail.get("1.0", tk.END))
        self.client.wait_for_cancel = True
        self.app.run_action("validate")
        self.app.cancel_event.set()
        self.complete()
        self.assertIn("취소됨", self.app.status.get())
        self.assertEqual(str(self.app.cancel_button["state"]), "disabled")

    def test_edit_requires_unchanged_preview_and_never_overwrites_original(self):
        with patch("document_workbench.filedialog.askopenfilename", return_value=str(self.markdown)):
            self.app.run_action("patch")
        self.complete()
        self.assertIsNotNone(self.app.edit_preview)
        self.markdown.write_text("# 다시 변경", encoding="utf-8")
        with patch("document_workbench.messagebox.showwarning") as warning:
            self.app.apply_edit()
        warning.assert_called_once()
        self.assertEqual(self.source.read_bytes(), b"original")
        self.assertIsNone(self.app.edit_preview)

    def test_successful_edit_saves_only_new_copy_and_partial_cannot_apply(self):
        with patch("document_workbench.filedialog.askopenfilename", return_value=str(self.markdown)):
            self.app.run_action("patch")
        self.complete()
        output = Path(self.temp.name) / "수정본.hwpx"
        with patch("document_workbench.filedialog.asksaveasfilename", return_value=str(output)):
            self.app.apply_edit()
        self.complete()
        self.assertEqual(output.read_bytes(), b"modified-copy")
        self.assertEqual(self.source.read_bytes(), b"original")
        self.assertEqual(self.client.calls[-1][1]["expected_fingerprints"], input_fingerprints([self.source, self.markdown]))
        self.client.partial = True
        with patch("document_workbench.filedialog.askopenfilename", return_value=str(self.markdown)):
            self.app.run_action("patch")
        self.complete()
        self.assertIsNone(self.app.edit_preview)
        self.assertEqual(str(self.app.apply_button["state"]), "disabled")
        self.assertIn("수정본은 저장하지 않았습니다", self.app.status.get())

    def test_edit_rechecks_files_after_save_dialog(self):
        with patch("document_workbench.filedialog.askopenfilename", return_value=str(self.markdown)):
            self.app.run_action("patch")
        self.complete()
        output = Path(self.temp.name) / "수정본.hwpx"
        def change_during_dialog(**_kwargs):
            self.markdown.write_text("# 미검토 변경", encoding="utf-8")
            return str(output)
        with patch("document_workbench.filedialog.asksaveasfilename", side_effect=change_during_dialog), patch("document_workbench.messagebox.showwarning") as warning:
            self.app.apply_edit()
        warning.assert_called_once()
        self.assertFalse(output.exists())
        self.assertEqual(len(self.client.calls), 1)

    def test_export_blocks_input_overwrite_and_saves_report(self):
        self.app.run_action("parse")
        self.complete()
        with patch("document_workbench.filedialog.asksaveasfilename", return_value=str(self.source)), patch("document_workbench.messagebox.showerror") as error:
            self.app.save_report()
        error.assert_called_once()
        self.assertEqual(self.source.read_bytes(), b"original")
        report = Path(self.temp.name) / "보고서.json"
        with patch("document_workbench.filedialog.asksaveasfilename", return_value=str(report)):
            self.app.save_report()
        self.assertIn("markdown", report.read_text(encoding="utf-8"))

    def test_page_navigation_produces_local_browser_preview(self):
        with patch("document_workbench.webbrowser.open", return_value=True) as browser:
            self.app.run_action("render")
            self.complete()
            self.app._change_page(1)
            self.complete()
        self.assertEqual(self.app.page.get(), "2")
        self.assertEqual(browser.call_count, 2)
        self.assertTrue(browser.call_args.args[0].startswith("file:"))
        local = Path(self.app._preview_files.name) / "page-2.html"
        self.assertIn("Content-Security-Policy", local.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
