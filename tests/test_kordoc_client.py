"""Adapter process safety and local HWPX editing integration coverage."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from kordoc_client import KordocClient


NODE = shutil.which("node")
ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(NODE, "Node.js unavailable")
class ClientProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="kordoc-client-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.package = self.directory / "package"
        (self.package / "dist").mkdir(parents=True)
        (self.package / "package.json").write_text('{"name":"kordoc"}', encoding="utf-8")
        (self.package / "dist" / "index.js").write_text("", encoding="utf-8")
        self.client = KordocClient(self.package, NODE, timeout=2)
        self.bridge = self.directory / "stub.mjs"
        self.client.bridge_path = self.bridge

    def stub(self, body):
        self.bridge.write_text("let s=''; for await (const c of process.stdin) s+=c; const req=JSON.parse(s);\n" + body, encoding="utf-8")

    def test_response_id_and_unicode(self):
        self.stub("process.stdout.write(JSON.stringify({id:req.id,action:req.action,ok:true,status:'success',data:req.args,warnings:[],error:null}));")
        result = self.client.request("parse", path=Path("한글 경로.hwpx"))
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["path"], "한글 경로.hwpx")

    def test_wrong_id_rejected(self):
        self.stub("process.stdout.write(JSON.stringify({id:'wrong',action:req.action,ok:true,status:'success',data:{},warnings:[],error:null}));")
        self.assertEqual(self.client.request("parse")["error"]["code"], "INVALID_RESPONSE")

    def test_partial_is_not_success(self):
        self.stub("process.stdout.write(JSON.stringify({id:req.id,action:req.action,ok:false,status:'partial',data:{applied:1},warnings:[],error:null}));")
        result = self.client.request("patch")
        self.assertEqual(result["status"], "partial")
        self.assertFalse(result["ok"])

    def test_timeout_is_bounded(self):
        self.stub("setInterval(()=>{},1000);")
        self.client.timeout = 0.15
        start = time.monotonic()
        self.assertEqual(self.client.request("parse")["error"]["code"], "TIMEOUT")
        self.assertLess(time.monotonic() - start, 3)

    def test_cancellation(self):
        self.stub("setInterval(()=>{},1000);")
        cancel = threading.Event()
        timer = threading.Timer(0.15, cancel.set)
        timer.start()
        self.addCleanup(timer.cancel)
        self.assertEqual(self.client.request("parse", cancel_event=cancel)["status"], "cancelled")

    def test_oversized_output_stops_process(self):
        self.stub("process.stdout.write('x'.repeat(100000)); setInterval(()=>{},1000);")
        with patch("kordoc_client.MAX_OUTPUT_BYTES", 4096):
            self.assertEqual(self.client.request("parse")["error"]["code"], "OUTPUT_TOO_LARGE")

    def test_no_node_preload_and_offline_environment(self):
        self.stub("process.stdout.write(JSON.stringify({id:req.id,action:req.action,ok:true,status:'success',data:{offline:process.env.KORDOC_OFFLINE,preload:process.env.NODE_OPTIONS||null},warnings:[],error:null}));")
        with patch.dict(os.environ, {"NODE_OPTIONS": "--require=missing-malicious-hook.js"}):
            result = self.client.request("diagnose")
        self.assertEqual(result["data"], {"offline": "1", "preload": None})

    def test_explicit_missing_package_does_not_fall_back(self):
        self.client.package_dir = self.directory / "missing"
        self.assertEqual(self.client.request("diagnose")["error"]["code"], "PACKAGE_NOT_FOUND")

    def test_pre_cancelled_does_not_start(self):
        cancel = threading.Event()
        cancel.set()
        with patch("kordoc_client.subprocess.Popen") as popen:
            self.assertEqual(self.client.request("parse", cancel_event=cancel)["status"], "cancelled")
            popen.assert_not_called()

    def test_bridge_blocks_network_and_child_process_fallbacks(self):
        self.client.bridge_path = ROOT / "kordoc_bridge.mjs"
        (self.package / "package.json").write_text('{"name":"kordoc","type":"module","version":"test"}', encoding="utf-8")
        source = self.directory / "source.hwpx"
        source.write_bytes(b"synthetic input")
        for operation in ("await fetch('https://example.test/not-contacted')",
                          "(await import('node:child_process')).spawn('nonexistent-executable')"):
            with self.subTest(operation=operation):
                (self.package / "dist" / "index.js").write_text(
                    f"export async function parse() {{ {operation}; return {{success:true,blocks:[],markdown:''}}; }}",
                    encoding="utf-8")
                result = self.client.request("parse", path=source)
                self.assertEqual(result["error"]["code"], "LOCAL_ONLY", result)

    def test_content_loss_in_source_is_partial_and_blocks_both_saves(self):
        self.client.bridge_path = ROOT / "kordoc_bridge.mjs"
        (self.package / "package.json").write_text('{"name":"kordoc","type":"module","version":"test"}', encoding="utf-8")
        (self.package / "dist" / "index.js").write_text("""
export async function parse(bytes) {return {success:true,markdown:'text',blocks:[],
 warnings:Buffer.from(bytes).toString()==='source'?[{code:'UNSUPPORTED_ELEMENT',message:'lost control text'}]:[]};}
export function diffBlocks(){return {stats:{added:0,removed:0,modified:0,unchanged:0},diffs:[]};}
export async function validateHwpx(){return {ok:true,issues:[],entryCount:1};}
export async function patchHwpx(){return {success:true,data:Buffer.from('patched'),applied:1,skipped:[],verification:diffBlocks()};}
export async function fillWithUniqueGuard(values,run){return {...await run(values),rejected:[]};}
export async function fillHwpx(){return {buffer:Buffer.from('filled'),filled:[],unmatched:[]};}
""", encoding="utf-8")
        source = self.directory / "warning.hwpx"
        source.write_bytes(b"source")
        markdown = self.directory / "edit.md"
        markdown.write_text("text", encoding="utf-8")
        values = self.directory / "values.json"
        values.write_text('{"label":"value"}', encoding="utf-8")
        output = self.directory / "result.hwpx"
        for action, kwargs in (("parse", {"path": source}),
                               ("compare", {"before": source, "after": source}),
                               ("patch", {"path": source, "markdown_file": markdown, "output": output, "dry_run": False}),
                               ("fill", {"path": source, "values_file": values, "output": output, "dry_run": False})):
            with self.subTest(action=action):
                result = self.client.request(action, **kwargs)
                self.assertEqual(result["status"], "partial", result)
                self.assertTrue(any(w.get("code") == "UNSUPPORTED_ELEMENT" for w in result["warnings"] if isinstance(w, dict)))
                self.assertFalse(output.exists())


@unittest.skipUnless(NODE, "Node.js unavailable")
class KordocIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = KordocClient(timeout=30)
        cls.package = cls.client._package()
        if cls.package is None:
            raise unittest.SkipTest("Optional pinned kordoc package not installed")
        cls.temp = tempfile.TemporaryDirectory(prefix="kordoc-integration-")
        cls.directory = Path(cls.temp.name)
        cls.source = cls.directory / "원본 문서.hwpx"
        cls.duplicate = cls.directory / "중복.hwpx"
        cls.long_before = cls.directory / "긴원본.hwpx"
        cls.long_after = cls.directory / "긴수정.hwpx"
        script = """
import {pathToFileURL} from 'node:url';
import fs from 'node:fs';
const api=await import(pathToFileURL(process.argv[1]).href);
fs.writeFileSync(process.argv[2],Buffer.from(await api.markdownToHwpx('# 제목 A\\n\\n학생 10명 참여\\n\\n| 학교명 | 기관 A |\\n| --- | --- |\\n| 인원 | 10명 |')));
fs.writeFileSync(process.argv[3],Buffer.from(await api.markdownToHwpx('담당: 대기\\n\\n담당: 대기')));
const longText='긴 문단 검증 '.repeat(80)+'대상A\\n\\n| 항목 | 내용 |\\n| --- | --- |\\n| 기관 | '+'반복 검증 '.repeat(80)+'원본A |';
fs.writeFileSync(process.argv[4],Buffer.from(await api.markdownToHwpx(longText)));
fs.writeFileSync(process.argv[5],Buffer.from(await api.markdownToHwpx(longText.replace('대상A','대상B').replace('원본A','원본B'))));
"""
        subprocess.run([NODE, "--input-type=module", "-e", script,
                        str(cls.package / "dist" / "index.js"), str(cls.source), str(cls.duplicate), str(cls.long_before), str(cls.long_after)],
                       check=True, capture_output=True, timeout=30,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_diagnose_and_parse_preserve_structure(self):
        diagnosis = self.client.request("diagnose")
        self.assertTrue(diagnosis["ok"], diagnosis)
        self.assertTrue(diagnosis["data"]["localOnly"])
        parsed = self.client.request("parse", path=self.source)
        self.assertTrue(parsed["ok"], parsed)
        self.assertIn("학생 10명", parsed["data"]["markdown"])
        tables = [b for b in parsed["data"]["blocks"] if b["type"] == "table"]
        self.assertEqual(tables[0]["table"]["cells"][1][0]["text"], "인원")
        self.assertEqual(tables[0]["table"]["cells"][1][0]["rowSpan"], 1)

    def test_patch_dryrun_save_compare_and_original_hash(self):
        before_hash = hashlib.sha256(self.source.read_bytes()).hexdigest()
        parsed = self.client.request("parse", path=self.source)["data"]
        edited = self.directory / "수정.md"
        edited.write_text(parsed["markdown"].replace("제목 A", "제목 B").replace("학생 10명", "학생 12명"), encoding="utf-8")
        destination = self.directory / "수정본.hwpx"
        preview = self.client.request("patch", path=self.source, markdown_file=edited, output=destination, dry_run=True)
        self.assertTrue(preview["ok"], preview)
        self.assertFalse(destination.exists())
        saved = self.client.request("patch", path=self.source, markdown_file=edited, output=destination, dry_run=False)
        self.assertTrue(saved["ok"], saved)
        self.assertEqual(saved["data"]["output"], str(destination.resolve()))
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), before_hash)
        comparison = self.client.request("compare", before=self.source, after=destination)
        self.assertTrue(comparison["ok"], comparison)
        self.assertGreater(comparison["data"]["stats"]["modified"], 0)
        self.assertEqual(comparison["data"]["diffs"][0]["beforeIndex"], 0)
        self.assertEqual(comparison["data"]["diffs"][0]["afterIndex"], 0)
        self.assertEqual(comparison["data"]["integrity"]["numbers"]["added"], [{"value": "12", "count": 1}])
        overwrite = self.client.request("patch", path=self.source, markdown_file=edited, output=destination, dry_run=False)
        self.assertEqual(overwrite["error"]["code"], "OUTPUT_EXISTS")
        original = self.client.request("patch", path=self.source, markdown_file=edited, output=self.source, dry_run=False)
        self.assertEqual(original["error"]["code"], "SOURCE_OVERWRITE")

    def test_preview_fingerprints_check_actual_source_markdown_and_values(self):
        markdown = self.directory / "fingerprint.md"
        markdown.write_text(self.client.request("parse", path=self.source)["data"]["markdown"], encoding="utf-8")
        values = self.directory / "fingerprint.json"
        values.write_text('{"학교명":"기관 B"}', encoding="utf-8")
        digest = lambda file: hashlib.sha256(file.read_bytes()).hexdigest()
        for action, input_file, option in (("patch", markdown, "markdown_file"), ("fill", values, "values_file")):
            with self.subTest(action=action):
                expected = {str(self.source.resolve()): digest(self.source), str(input_file.resolve()): digest(input_file)}
                valid = self.client.request(action, path=self.source, expected_fingerprints=expected, **{option: input_file})
                self.assertNotEqual((valid.get("error") or {}).get("code"), "INPUT_CHANGED", valid)
                for stale in (self.source, input_file):
                    altered = {**expected, str(stale.resolve()): "0" * 64}
                    destination = self.directory / f"stale-{action}-{stale.suffix[1:]}.hwpx"
                    result = self.client.request(action, path=self.source, output=destination, dry_run=False,
                                                 expected_fingerprints=altered, **{option: input_file})
                    self.assertEqual(result["error"]["code"], "INPUT_CHANGED", result)
                    self.assertFalse(destination.exists())
                missing = {str(self.source.resolve()): digest(self.source)}
                result = self.client.request(action, path=self.source, expected_fingerprints=missing, **{option: input_file})
                self.assertEqual(result["error"]["code"], "INPUT_CHANGED", result)

    def test_long_paragraph_and_cell_one_character_changes_are_not_unchanged(self):
        result = self.client.request("compare", before=self.long_before, after=self.long_after)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["data"]["stats"]["modified"], 2)
        table = next(diff for diff in result["data"]["diffs"] if diff["before"].get("table"))
        self.assertEqual((table["beforeIndex"], table["afterIndex"]), (1, 1))
        self.assertEqual((table["cellChanges"][0]["row"], table["cellChanges"][0]["col"]), (1, 1))
        self.assertTrue(table["cellChanges"][0]["before"].endswith("원본A"))
        self.assertTrue(table["cellChanges"][0]["after"].endswith("원본B"))

    def test_partial_patch_never_publishes(self):
        parsed = self.client.request("parse", path=self.source)["data"]
        edited = self.directory / "unsupported.md"
        edited.write_text(parsed["markdown"] + "\n\n추가된 새 문단", encoding="utf-8")
        destination = self.directory / "부분.hwpx"
        result = self.client.request("patch", path=self.source, markdown_file=edited, output=destination, dry_run=False)
        self.assertEqual(result["status"], "partial", result)
        self.assertIsNone(result["data"]["output"])
        self.assertFalse(destination.exists())

    def test_unique_fill_guard(self):
        values = self.directory / "중복값.json"
        values.write_text(json.dumps({"담당": "비식별 담당"}, ensure_ascii=False), encoding="utf-8")
        result = self.client.request("fill", path=self.duplicate, values_file=values)
        self.assertEqual(result["status"], "partial", result)
        self.assertTrue(result["data"]["rejected"])

    def test_validate_fields_profile_lint_and_render(self):
        for action in ("validate", "fields", "profile", "lint", "render"):
            with self.subTest(action=action):
                result = self.client.request(action, path=self.source)
                self.assertTrue(result["ok"], result)
                if action == "fields":
                    self.assertTrue(result["data"]["fields"])
                if action == "render":
                    self.assertIn("<svg", result["data"]["svg"])
                    self.assertGreaterEqual(result["data"]["pageCount"], 1)
        self.assertEqual(self.client.request("render", path=self.source, page=0)["error"]["code"], "INVALID_PAGE")

    def test_corrupt_document_and_external_image_fail_closed(self):
        corrupt = self.directory / "corrupt.hwpx"
        corrupt.write_bytes(b"not a document")
        self.assertFalse(self.client.request("parse", path=corrupt)["ok"])
        external = self.directory / "external.md"
        external.write_text("![image](https://example.test/pixel.png)", encoding="utf-8")
        result = self.client.request("patch", path=self.source, markdown_file=external)
        self.assertEqual(result["error"]["code"], "LOCAL_ONLY")


if __name__ == "__main__":
    unittest.main()
