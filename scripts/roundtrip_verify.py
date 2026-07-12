"""HWPX 내용 보존 라운드트립 검증 (수동 실행 — 네이티브 Windows + 한컴오피스 필요).

파이프라인:
  1. 샘플 Markdown → HWPX  (anyway_to_hwpx_com.py, HWP COM)
  2. HWPX → Markdown       (kordoc CLI, Node)
  3. 원본 md의 표 셀·문단 텍스트가 역파싱 결과에 모두 남아 있는지 대조

COM·kordoc CLI가 필요하므로 pytest 기본 스위트(COM-free)에는 포함하지 않는다.
이것은 테두리(§8-6) 작업의 회귀 가드가 아니라 일반 내용 보존 스모크 체크다.

사용:
  python scripts/roundtrip_verify.py                # 번들 샘플 사용
  python scripts/roundtrip_verify.py 문서.md         # 임의 md 검증
  KORDOC_CLI=경로/cli.js python scripts/roundtrip_verify.py

종료 코드: 0 = 모든 토큰 보존, 1 = 누락 발견, 2 = 환경 미비(COM·CLI 없음)
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

DEFAULT_KORDOC_CLI = Path(r"C:/Users/홍주형/mcp-servers/kordoc/node_modules/kordoc/dist/cli.js")

SAMPLE_MD = """# 라운드트립 내용 검증

## 프로그램 현황

| 구분 | 인원 | 주요 내용 | 비고 |
| --- | --- | --- | --- |
| 초등 | 120 | 자연 생태 체험학습 운영 | 상반기 |
| 중등 | 95 | 역사 평화 탐방 프로그램 | 하반기 |
| 합계 | 215 | 강화도 연계 통합 운영 | - |

본 프로그램은 강화도의 자연·역사·평화 자원을 연계하여 운영한다.
"""


def _configure_utf8() -> None:
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _resolve_kordoc_cli() -> Path | None:
    override = os.environ.get("KORDOC_CLI")
    if override:
        candidate = Path(override)
        return candidate if candidate.exists() else None
    return DEFAULT_KORDOC_CLI if DEFAULT_KORDOC_CLI.exists() else None


def _normalize(text: str) -> str:
    """공백·불릿·표 구분선을 걷어낸 비교용 정규화."""
    text = text.replace(" ", " ")
    return re.sub(r"\s+", " ", text).strip()


def source_tokens(markdown: str) -> list[str]:
    """원본 md에서 보존되어야 할 표 셀·문단 텍스트 토큰을 추출."""
    tokens: list[str] = []
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            continue
        if re.fullmatch(r"\|?[\s:|-]+\|?", line):  # 표 구분선(---)
            continue
        if line.startswith("|"):
            for cell in line.strip("|").split("|"):
                value = _normalize(cell)
                if value and value != "-":
                    tokens.append(value)
        else:
            value = _normalize(re.sub(r"^#+\s*", "", line))
            if value:
                tokens.append(value)
    return tokens


def convert_md_to_hwpx(md_path: Path, out_dir: Path) -> Path:
    result = subprocess.run(
        [sys.executable, str(REPO / "anyway_to_hwpx_com.py"), str(md_path), "-o", str(out_dir)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    hwpx = out_dir / (md_path.stem + ".hwpx")
    if not hwpx.exists():
        raise RuntimeError(
            f"변환 산출물 없음: {hwpx}\nstdout: {result.stdout.strip()}\nstderr: {result.stderr.strip()}"
        )
    return hwpx


def parse_hwpx_to_md(cli: Path, hwpx_path: Path, out_dir: Path) -> str:
    out_md = out_dir / (hwpx_path.stem + ".parsed.md")
    result = subprocess.run(
        ["node", str(cli), str(hwpx_path), "-o", str(out_md), "--silent"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"kordoc 파싱 실패 (code {result.returncode}): {result.stderr.strip()}")
    if out_md.exists():
        return out_md.read_text(encoding="utf-8")
    return result.stdout


def verify(markdown: str) -> tuple[list[str], str]:
    """(누락 토큰 목록, 역파싱 md) 반환."""
    cli = _resolve_kordoc_cli()
    if cli is None:
        raise EnvironmentError("kordoc CLI를 찾을 수 없음 (KORDOC_CLI 환경변수로 지정)")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        md_path = tmp_dir / "roundtrip_source.md"
        md_path.write_text(markdown, encoding="utf-8")
        hwpx = convert_md_to_hwpx(md_path, tmp_dir)
        parsed = parse_hwpx_to_md(cli, hwpx, tmp_dir)
    haystack = _normalize(parsed)
    missing = [token for token in source_tokens(markdown) if _normalize(token) not in haystack]
    return missing, parsed


def main(argv: list[str]) -> int:
    _configure_utf8()
    if len(argv) > 1:
        markdown = Path(argv[1]).read_text(encoding="utf-8")
        label = argv[1]
    else:
        markdown = SAMPLE_MD
        label = "(번들 샘플)"

    try:
        missing, parsed = verify(markdown)
    except EnvironmentError as exc:
        print(f"[건너뜀] {exc}", file=sys.stderr)
        return 2

    tokens = source_tokens(markdown)
    print(f"검증 대상: {label}")
    print(f"토큰 {len(tokens)}개 중 보존 {len(tokens) - len(missing)}개 / 누락 {len(missing)}개")
    if missing:
        print("\n[누락된 내용]")
        for token in missing:
            print(f"  - {token}")
        print("\n[역파싱 결과 일부]")
        print("\n".join(parsed.splitlines()[:30]))
        return 1
    print("모든 표 셀·문단 텍스트가 라운드트립에서 보존됨.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
