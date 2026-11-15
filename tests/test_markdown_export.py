"""HWP·HWPX·PDF → Markdown export: naming, publication, cleanup and bridge safety."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import quote

import anyway_to_hwpx_com as converter
import document_cli
from kordoc_client import KordocClient
import markdown_export
from markdown_export_window import run_markdown_batch

NODE = shutil.which("node")
ROOT = Path(__file__).resolve().parents[1]
# 1x1 PNG
_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6360606060000000050001a5f645400000000049454e44ae426082"
)


class FakeClient:
    """Writes what the bridge would write into the staging folder it is given."""

    def __init__(self, status="success", images=1, fail_after_write=False, warnings=()):
        self.status, self.images, self.fail_after_write, self.warnings = status, images, fail_after_write, list(warnings)
        self.calls = []

    def request(self, action, *, cancel_event=None, **kwargs):
        self.calls.append((action, kwargs))
        staging = Path(kwargs["staging_dir"])
        image_dir = kwargs["image_dir_name"]
        if self.images:
            (staging / image_dir).mkdir()
            (staging / image_dir / "image_001.png").write_bytes(b"png")
        (staging / "document.md").write_text(f"# 제목\n\n![image]({quote(image_dir)}/image_001.png)\n", encoding="utf-8")
        if self.fail_after_write:
            return {"ok": False, "status": "error", "action": action, "data": None, "warnings": [],
                    "error": {"code": "TIMEOUT", "message": "시간 초과"}}
        return {"ok": self.status == "success", "status": self.status, "action": action, "warnings": self.warnings,
                "error": None, "data": {"imageDir": image_dir if self.images else None,
                                        "images": [{"name": "image_001.png"}] if self.images else []}}


class ExportPublicationTests(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.root = Path(self._temp.name)
        self.source = self.root / "원본 문서.hwpx"
        self.source.write_bytes(b"source")
        self.out = self.root / "출력"

    def test_publishes_markdown_and_image_folder_and_removes_staging(self):
        result = markdown_export.convert_to_markdown(self.source, self.out, client=FakeClient())
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(sorted(p.name for p in self.out.iterdir()), ["원본 문서.md", "원본 문서_images"])
        self.assertEqual(result["data"]["output"], str(self.out / "원본 문서.md"))
        self.assertTrue((self.out / "원본 문서_images" / "image_001.png").is_file())

    def test_existing_outputs_are_never_replaced(self):
        self.out.mkdir()
        (self.out / "원본 문서.md").write_text("기존", encoding="utf-8")
        (self.out / "원본 문서 - 2_images").mkdir()
        result = markdown_export.convert_to_markdown(self.source, self.out, client=FakeClient())
        self.assertEqual(result["data"]["output"], str(self.out / "원본 문서 - 3.md"))
        self.assertEqual((self.out / "원본 문서.md").read_text(encoding="utf-8"), "기존")
        self.assertEqual(list((self.out / "원본 문서 - 2_images").iterdir()), [])

    def test_failure_or_timeout_leaves_nothing_behind(self):
        result = markdown_export.convert_to_markdown(self.source, self.out, client=FakeClient(fail_after_write=True))
        self.assertEqual(result["error"]["code"], "TIMEOUT")
        self.assertEqual(list(self.out.iterdir()), [])

    def test_cancel_after_bridge_returns_does_not_publish(self):
        cancel = threading.Event()
        cancel.set()
        result = markdown_export.convert_to_markdown(self.source, self.out, client=FakeClient(), cancel_event=cancel)
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(list(self.out.iterdir()), [])

    def test_partial_result_is_saved_and_reported(self):
        result = markdown_export.convert_to_markdown(
            self.source, self.out, client=FakeClient(status="partial", images=0, warnings=["그림 1개 누락"]))
        self.assertEqual(result["status"], "partial")
        self.assertIsNone(result["data"]["imageDir"])
        self.assertEqual([p.name for p in self.out.iterdir()], ["원본 문서.md"])

    def test_unsupported_input_is_refused_before_starting(self):
        docx = self.root / "a.docx"
        docx.write_bytes(b"x")
        client = FakeClient()
        self.assertEqual(markdown_export.convert_to_markdown(docx, self.out, client=client)["error"]["code"], "UNSUPPORTED_FORMAT")
        self.assertEqual(client.calls, [])

    def test_exported_markdown_is_never_deleted_by_emptying_the_hwpx_output_folder(self):
        # Exported Markdown is meant to be edited; "저장 폴더 비우기" must stop instead of deleting it.
        converter.prepare_output_dir(self.out, empty_output_folder=True)
        markdown_export.convert_to_markdown(self.source, self.out, client=FakeClient())
        with self.assertRaises(RuntimeError):
            converter.prepare_output_dir(self.out, empty_output_folder=True)
        self.assertTrue((self.out / "원본 문서.md").is_file())
        self.assertTrue((self.out / "원본 문서_images" / "image_001.png").is_file())

    def test_exported_links_import_back_as_images_for_awkward_names(self):
        # The app's own Markdown → HWPX importer must read the exported links back as images.
        for stem in ("운영계획(안)", "보고 - 2", "100% 달성#1"):
            with self.subTest(stem=stem):
                folder = self.out / f"{stem}_images"
                folder.mkdir(parents=True)
                (folder / "image_001.png").write_bytes(_PNG)
                link = stem.replace("%", "%25").replace(" ", "%20").replace("(", "%28").replace(")", "%29").replace("#", "%23")
                blocks = converter.parse_markdown(f"본문\n\n![image]({link}_images/image_001.png)\n", source_dir=self.out)
                self.assertEqual([b["type"] for b in blocks], ["p", "image"], blocks)
                self.assertEqual(Path(blocks[1]["path"]), (folder / "image_001.png").resolve())

    def test_batch_reports_counts_and_stops_on_cancel(self):
        messages, cancel = [], threading.Event()
        other = self.root / "둘째.pdf"
        other.write_bytes(b"pdf")

        def sink(message):
            messages.append(message)
            if message[0] == "log" and message[1].startswith("완료"):
                cancel.set()

        counts = run_markdown_batch((str(self.source), str(other)), str(self.out), True, sink, cancel, client=FakeClient())
        self.assertEqual(counts, {"success": 1, "partial": 0, "error": 0, "cancelled": 1})
        self.assertEqual(messages[-1], ("done", counts))

    def test_cli_to_md_uses_the_same_export(self):
        output = []

        class Stream:
            write = output.append

        code = document_cli.main(["to-md", str(self.source), "--output-dir", str(self.out)], client=FakeClient(), stdout=Stream())
        self.assertEqual(code, 0)
        self.assertEqual(json.loads("".join(output))["data"]["output"], str(self.out / "원본 문서.md"))


@unittest.skipUnless(NODE, "Node.js unavailable")
class BridgeImageNameTests(unittest.TestCase):
    """A hostile container entry name must never become a disk path."""

    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.root = Path(self._temp.name)
        self.package = self.root / "package"
        (self.package / "dist").mkdir(parents=True)
        (self.package / "package.json").write_text('{"name":"kordoc","type":"module","version":"test"}', encoding="utf-8")
        self._stub("""
export async function parse() { return { success: true, fileType: 'hwpx', pageCount: 1, warnings: [],
  markdown: '# 제목\\n\\n![a](../../evil.png)\\n\\n![b](missing.png)\\n',
  images: [{ filename: '../../evil.png', mimeType: 'image/png', data: new Uint8Array([1, 2, 3]) },
           { filename: 'x.exe', mimeType: 'application/x-msdownload', data: new Uint8Array([4]) }] }; }
""")
        self.client = KordocClient(self.package, NODE, timeout=10)
        self.client.bridge_path = ROOT / "kordoc_bridge.mjs"
        environment = patch.dict(os.environ, {"HWPX_KORDOC_ALLOW_UNREVIEWED": "1"})
        environment.start()
        self.addCleanup(environment.stop)
        self.source = self.root / "work" / "문서.hwpx"
        self.source.parent.mkdir()
        self.source.write_bytes(b"synthetic")

    def _stub(self, source):
        (self.package / "dist" / "index.js").write_text(source, encoding="utf-8")

    def test_images_get_generated_names_and_dangling_references_are_partial(self):
        out = self.root / "work" / "out"
        result = markdown_export.convert_to_markdown(self.source, out, client=self.client)
        self.assertEqual(result["status"], "partial", result)
        self.assertFalse((self.root / "evil.png").exists())
        self.assertEqual(sorted(p.name for p in (out / "문서_images").iterdir()), ["image_001.png"])
        markdown = (out / "문서.md").read_text(encoding="utf-8")
        self.assertIn("![a](문서_images/image_001.png)", markdown)
        self.assertNotIn("evil", markdown)
        self.assertEqual(result["data"]["danglingImages"], 1)

    def test_parentheses_in_document_name_keep_links_valid(self):
        self._stub("""
export async function parse() { return { success: true, fileType: 'hwp', warnings: [],
  markdown: '본문\\n\\n![image](image_001.bmp)\\n',
  images: [{ filename: 'image_001.bmp', mimeType: 'image/png', data: new Uint8Array([1]) }] }; }
""")
        source = self.source.with_name("운영계획(안).hwp")
        source.write_bytes(b"synthetic")
        out = self.root / "work" / "out"
        result = markdown_export.convert_to_markdown(source, out, client=self.client)
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(result["data"]["danglingImages"], 0)
        self.assertIn("![image](운영계획%28안%29_images/image_001.png)", (out / "운영계획(안).md").read_text(encoding="utf-8"))

    def test_pages_without_text_layer_are_partial(self):
        self._stub("""
export async function parse() { return { success: true, fileType: 'pdf', pageCount: 2, warnings: [], images: [],
  markdown: '1쪽 본문', pageQuality: [{ page: 1, needsOcr: false }, { page: 2, needsOcr: true }] }; }
""")
        source = self.source.with_suffix(".pdf")
        source.write_bytes(b"synthetic")
        result = markdown_export.convert_to_markdown(source, self.root / "work" / "out", client=self.client)
        self.assertEqual(result["status"], "partial", result)
        self.assertEqual(result["data"]["ocrPages"], [2])
        self.assertTrue(any("2쪽" in w for w in result["warnings"] if isinstance(w, str)))

    def test_heap_exhaustion_is_reported_as_out_of_memory(self):
        stub = self.root / "oom.mjs"
        stub.write_text("process.stderr.write('FATAL ERROR: Reached heap limit Allocation failed - JavaScript heap out of memory\\n');"
                        "process.exit(134);", encoding="utf-8")
        self.client.bridge_path = stub
        result = self.client.request("to_markdown", path=str(self.source))
        self.assertEqual(result["error"]["code"], "OUT_OF_MEMORY", result)
        self.assertNotIn("FATAL", json.dumps(result, ensure_ascii=False))

    def test_bridge_rejects_staging_outside_its_contract(self):
        for staging, name in ((str(self.root), "문서_images"), (str(self.root / "missing"), "문서_images")):
            with self.subTest(staging=staging):
                result = self.client.request("to_markdown", path=str(self.source), staging_dir=staging, image_dir_name=name)
                self.assertEqual(result["status"], "error", result)
        staging = self.root / ".to-md-x"
        staging.mkdir()
        for name in ("../escape", "a/b", "", "con<"):
            with self.subTest(name=name):
                result = self.client.request("to_markdown", path=str(self.source), staging_dir=str(staging), image_dir_name=name)
                self.assertEqual(result["error"]["code"], "INVALID_OUTPUT_NAME", result)
        self.assertEqual(list(staging.iterdir()), [])


@unittest.skipUnless(NODE and (ROOT / "deps" / "kordoc" / "node_modules" / "kordoc").is_dir(), "pinned kordoc not installed")
class RealPackageExportTests(unittest.TestCase):
    def test_kordoc_generated_hwpx_becomes_markdown(self):
        client = KordocClient(timeout=60)
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "보고서.hwpx"
            script = ("import {pathToFileURL} from 'node:url'; import fs from 'node:fs';"
                      "const api=await import(pathToFileURL(process.argv[1]).href);"
                      "fs.writeFileSync(process.argv[2],Buffer.from(await api.markdownToHwpx("
                      "'# 추진 계획\\n\\n학생 10명 참여\\n\\n| 구분 | 인원 |\\n| --- | --- |\\n| 초등 | 10명 |')));")
            subprocess.run([NODE, "--input-type=module", "-e", script,
                            str(client._package() / "dist" / "index.js"), str(source)],
                           check=True, capture_output=True, timeout=60,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            result = markdown_export.convert_to_markdown(source, Path(temp) / "out", client=client)
            self.assertEqual(result["status"], "success", result)
            markdown = Path(result["data"]["output"]).read_text(encoding="utf-8")
            self.assertIn("추진 계획", markdown)
            self.assertIn("학생 10명", markdown)
            self.assertIn("| 초등 | 10명 |", markdown)


if __name__ == "__main__":
    unittest.main()
