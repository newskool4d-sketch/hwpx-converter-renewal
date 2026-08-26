"""HWPX 편집기 안전성 게이트 (상설화, Track E-3).

한컴오피스가 열람할 수 있는 최소 구조 조건을 실변환 없이 점검한다.
python-hwpx 6.0.2의 `editor_safety_gate` CLI가 이번 환경(2.8.3)에는 없어
동일 목적을 달성하는 두 검사기를 조합했다:

  1. hwpx.tools.package_validator.validate_package
     ZIP/컨테이너/매니페스트 구조(mimetype, container.xml, 파트 참조 무결성)
  2. hwpx.tools.validator.validate_document
     header.xml·section*.xml의 OWPML 스키마 적합성

두 검사 모두 08b2130이 검출했던 종류의 결함(XML 선언·네임스페이스 누락,
파트 참조 깨짐)을 실물 HWP 실행 없이 잡아낸다.

사용:
  python scripts/hwpx_editor_safety_gate.py 산출물.hwpx [산출물2.hwpx ...]
  python scripts/hwpx_editor_safety_gate.py --strict 산출물.hwpx   # 경고도 실패로 취급

종료 코드: 0 = 통과(strict 미지정 시 경고 허용), 1 = 오류 발견, 2 = 환경 미비(python-hwpx 없음)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def _configure_utf8() -> None:
    import os

    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _check_one(path: Path, *, strict: bool) -> bool:
    from hwpx.tools.package_validator import validate_package
    from hwpx.tools.validator import validate_document

    print(f"\n=== {path} ===")
    ok = True

    package_report = validate_package(path)
    for issue in package_report.issues:
        prefix = "ERROR" if issue.is_error else "WARN"
        print(f"[package] {prefix}: {issue}")
    if not package_report.ok:
        ok = False
    elif strict and package_report.warnings:
        ok = False

    if package_report.ok:
        try:
            doc_report = validate_document(path)
        except Exception as exc:  # 스키마 로드·문서 파싱 실패는 오류로 취급
            print(f"[schema] ERROR: {exc}")
            ok = False
        else:
            for issue in doc_report.issues:
                print(f"[schema] ERROR: {issue}")
            if not doc_report.ok:
                ok = False
            if doc_report.ok and not doc_report.issues:
                print(f"[schema] validated {len(doc_report.validated_parts)} part(s), no issues")
    else:
        print("[schema] skipped (package structure invalid)")

    print(f"=== {'PASS' if ok else 'FAIL'}: {path} ===")
    return ok


def main(argv: list[str] | None = None) -> int:
    _configure_utf8()

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sources", nargs="+", type=Path, help="검사할 .hwpx 파일 경로(들)")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="구조 검사 경고도 실패로 취급한다.",
    )
    args = parser.parse_args(argv)

    try:
        import hwpx  # noqa: F401
    except ImportError:
        print(
            "python-hwpx가 설치되어 있지 않습니다. "
            "`pip install python-hwpx` 후 다시 실행하세요.",
            file=sys.stderr,
        )
        return 2

    all_ok = True
    for source in args.sources:
        if not source.exists():
            print(f"[skip] 파일 없음: {source}", file=sys.stderr)
            all_ok = False
            continue
        if not _check_one(source, strict=args.strict):
            all_ok = False

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
