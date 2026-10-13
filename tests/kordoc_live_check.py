"""Non-identifying live checks against the parent's Hancom-generated samples.

Run explicitly, after out/baseline-hancom samples exist. No COM invocation here.
"""
import hashlib
import json
from pathlib import Path
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from kordoc_client import KordocClient


def main():
    client = KordocClient(timeout=60)
    baseline = ROOT / "out" / "baseline-hancom"
    output = ROOT / "out" / "kordoc-integration"
    output.mkdir(exist_ok=True)
    checks = []

    def check(action, **kwargs):
        started = time.monotonic()
        result = client.request(action, **kwargs)
        data = result.get("data") or {}
        checks.append({"action": action, "input": Path(kwargs.get("path", kwargs.get("before", ""))).name,
                       "status": result["status"], "seconds": round(time.monotonic() - started, 3),
                       "warnings": result["warnings"], "error": result["error"],
                       "output": data.get("output"), "summary": data.get("summary"),
                       "validation": data.get("validation"), "stats": data.get("stats"),
                       "dryRun": data.get("dryRun"), "applied": data.get("applied"),
                       "unmatched": data.get("unmatched"), "rejected": data.get("rejected")})
        print(action, checks[-1]["input"], result["status"], flush=True)
        return result

    check("diagnose")
    for name in ("sample", "tables", "sheet", "sihaengmun"):
        source = baseline / f"{name}.hwpx"
        for action in ("parse", "validate", "fields", "profile", "lint", "render"):
            result = check(action, path=source)
            if action == "render" and result["ok"]:
                (output / f"{name}-page-1.svg").write_text(result["data"]["svg"], encoding="utf-8")
        check("compare", before=source, after=source)
    for name in ("sample", "tables"):
        check("parse", path=baseline / f"{name}.pdf")

    source = baseline / "sample.hwpx"
    original = source.read_bytes()
    parsed = check("parse", path=source)
    markdown = output / "sample-edited.md"
    markdown.write_text(parsed["data"]["markdown"].replace("리뉴얼 테스트", "리뉴얼 비교 검증", 1), encoding="utf-8")
    values = output / "sample-values.json"
    values.write_text(json.dumps({"제목": "리뉴얼 양식 검증"}, ensure_ascii=False), encoding="utf-8")
    for action, options in (("patch", {"markdown_file": markdown}), ("fill", {"values_file": values})):
        check(action, path=source, dry_run=True, **options)
        destination = output / f"sample-{action}-{time.time_ns()}.hwpx"
        result = check(action, path=source, output=destination, dry_run=False, **options)
        if result["ok"] and destination.exists():
            check("compare", before=source, after=destination)
            with zipfile.ZipFile(source) as before, zipfile.ZipFile(destination) as after:
                untouched = [name for name in before.namelist() if not name.startswith("Contents/section")]
                checks.append({"action": "zip-preservation", "input": destination.name,
                               "unchangedEntries": len(untouched),
                               "status": "success" if all(before.read(n) == after.read(n) for n in untouched) else "error"})
    checks.append({"action": "source-hash", "status": "success" if source.read_bytes() == original else "error",
                   "sha256": hashlib.sha256(original).hexdigest()})
    report = {"checks": checks, "success": sum(c["status"] == "success" for c in checks),
              "partial": sum(c["status"] == "partial" for c in checks),
              "error": sum(c["status"] == "error" for c in checks)}
    (output / "live-check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("success", "partial", "error")}), flush=True)


if __name__ == "__main__":
    main()
