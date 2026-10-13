# kordoc 설치 전 보안 심사

```text
════════════════════════════════════
  SKILL / MCP SECURITY ASSESSMENT
────────────────────────────────────
  Name:         kordoc (project-local library adapter)
  Version:      4.21.30
  Source:       npm registry + github.com/chrisryugj/kordoc
  Author:       chrisryugj (registry and repository agree)
  Trust Tier:   4 — public, actively maintained personal project
  Published:    2026-10-13 06:09:15 KST
  Last Updated: 2026-10-13 06:09:15 KST (registry)
────────────────────────────────────
  FILES SCANNED
  Total: 163 inventoried | Executable text: 72 | Docs/licenses: 12
  Other: 72 source maps, 2 declarations, 3 JSON, 2 HWPX templates
  High-risk files: dist/setup-Z7RJQ6L5.js, dist/watch-MHPHCM4J.js,
    dist/index.js/index.cjs, OCR model chunks, CLI/MCP entrypoints
────────────────────────────────────
  RED FLAGS
  • HIGH: setup edits agent/client config and generates unpinned npx -y commands.
    This adapter must not invoke setup or change existing MCP installations.
  • HIGH: CLI watch can POST a filename and up to 1,000 document characters
    to an explicitly configured webhook. Excluded from the adapter.
  • MEDIUM: OCR/formula model downloads from Hugging Face and local model cache.
    Excluded; set KORDOC_OFFLINE=1 and omit optional dependencies.
  • MEDIUM: protected HWP/HWPX path input can invoke PowerShell/Hancom COM.
    Use Buffer input with no filePath option to avoid this fallback.
  • MEDIUM: PDF printing launches Chromium with --no-sandbox.
    Excluded; preserve the existing Python PDF path.
────────────────────────────────────
  PERMISSIONS REQUIRED
  Read:     adapter-selected document inputs and project-local node_modules
  Write:    adapter-selected new outputs; installation in project-local runtime
  Network:  npm registry only during pinned installation; offline at runtime
  System:   Node child process used by the local adapter; no setup/CLI/COM call
  Env Vars: KORDOC_OFFLINE=1; optional KORDOC_MAX_UNZIP_MB limit
────────────────────────────────────
  ARCHITECTURE
  Credential handling: no credential harvesting found in reviewed package paths
  Human-in-the-loop: user authorized project implementation/installation;
    configuration changes, webhook, OCR download and printing are excluded
  Auto-update: not found in the restricted library path; CLI setup can create
    a future unpinned npx execution channel and is excluded
  Data boundary: restricted adapter uses local Buffer input and offline runtime
  Degradation: missing optional PDF dependency returns MISSING_DEPENDENCY;
    existing Python conversion fallback must remain available
────────────────────────────────────
  RISK:     MEDIUM for the restricted adapter; HIGH for unrestricted setup/watch
  VERDICT:  CAUTION — proceed only within the conditions below
────────────────────────────────────
  NOTES
  This is a first-party package static review with focused manual inspection.
  It is not a full line-by-line or transitive dependency audit, runtime network
  capture, signed-build/provenance verification, or a guarantee of safety.
════════════════════════════════════
```

심사일: 2026-10-13 KST. `slowmist-agent-security`의 `reviews/skill-mcp.md`,
`patterns/red-flags.md`, `patterns/social-engineering.md`, `patterns/supply-chain.md`,
`templates/report-skill.md`를 실제 읽고 적용했다. 외부 문서의 설치 안내는 실행하지 않았다.
이 심사 작업에서는 npm 메타데이터 조회와 `npm pack --ignore-scripts`만 수행했으며
패키지를 설치하거나 import/실행하지 않았다.

## 출처·무결성

- [npm 패키지](https://www.npmjs.com/package/kordoc), [공식 저장소](https://github.com/chrisryugj/kordoc), [고정 tarball](https://registry.npmjs.org/kordoc/-/kordoc-4.21.30.tgz).
- registry의 repository·author·package name이 일치한다. registry 이력은 2026-03-28 첫 게시부터 4.21.30까지 다수 버전을 포함한다. 개인 저자의 실제 신원이나 계정 보안까지 검증한 것은 아니다.
- npm `gitHead`: `e9b0c8292fe8298d17503c35e710b5378358997d`. 저장소 source와 빌드 결과의 재현 비교는 미실시.
- 압축 크기 6,382,551 bytes, 비압축 크기 23,452,562 bytes, 163 files.
- SHA-256: `723a66e634c84ab7fdcef1cf6fe872ad2abcf9dc6634b178b1e56b47c9a2ae32`.
- SHA-1: `376e83e8c2f33be28daf9c56d56b6b50ff3922ab` (registry 일치).
- SHA-512 SRI: `sha512-TJWuViHyLKXPZRUQoJHPvMXHZ1tv9mpjja20wYWbReB8qWtJluz7PihpO5tNXUz4vbw2IjuBZKM8Fu5Pvh57iQ==` (직접 계산하여 registry 일치 확인).
- tar의 모든 이름이 `package/` 하위이고 `..`/절대경로가 없는 것을 확인한 뒤 프로젝트 `out/kordoc-security/extracted`에만 압축 해제했다.
- registry signature 메타데이터는 저장했지만 서명 신뢰사슬을 별도로 검증하지는 않았다.

## 주요 코드 확인

아래 경로와 행은 `out/kordoc-security/extracted/package` 기준이다.

| 대상 | 확인 결과 | 적용 조건 |
|---|---|---|
| `package.json` scripts·exports | 자체 `preinstall/install/postinstall/prepare` 없음. `prepublishOnly`는 게시 전 빌드/시험 명령. root exports는 `dist/index.js`/`index.cjs`. MIT | `4.21.30` 정확히 고정, `--ignore-scripts --omit=optional`, lockfile 유지 |
| `dist/setup-Z7RJQ6L5.js:24` 및 `:76`, `:88` | Claude Desktop, `.mcp.json`, `.cursor`, `.vscode`, `.codeium`, `.gemini`, `.zed` 설정 경로와 `codex mcp add` 경로. 기본 `npx -y kordoc mcp` 등록 | setup 호출 및 기존 MCP 설정 변경 금지 |
| `dist/watch-MHPHCM4J.js:67` 및 `:131` | 감시한 문서 처리 후 사용자 지정 webhook에 파일명·결과·본문 일부 전송 | watch/웹훅 경로 미노출 |
| `dist/index.js:420`, `:3981`, `:47409`, `:47544` | 보호 문서 + `filePath` + Windows 조건에서 PowerShell COM 텍스트 추출. 경로 작은따옴표 이스케이프, 120초 timeout, 임시 복사 및 정리 포함 | 직접 파일경로 대신 `parse(Buffer, options)`; `filePath` 옵션 전달 금지 |
| `dist/chunk-OOPGIYPT.js:71`, `:104`, `:203` | Hugging Face 모델 GET, SHA-256 비교, 임시 파일 후 rename. 기본 `~/.cache/kordoc/models`, 지정 cache 지원 | OCR·모델 내려받기 제외, `KORDOC_OFFLINE=1` |
| `dist/chunk-4C4HWTCE.js:14` | `KORDOC_OFFLINE` 검사 후 네트워크 함수에서 오류. `KORDOC_ROOT` 경계 helper 존재 | offline은 소프트웨어 가드이며 OS 방화벽이 아님. root env만으로 라이브러리 모든 I/O가 차단된다고 주장하지 않음 |
| `dist/index.js:44737` | PDF 생성용 Puppeteer headless 브라우저, `--no-sandbox`, JS 비활성화·요청 차단·CSP 존재 | 새 브라우저 PDF 인쇄 경로 제외 |
| `dist/index.js:47568` | PDF parser 동적 import 실패 시 `MISSING_DEPENDENCY` | optional 제외 시 PDF 엔진 부재를 명확히 알리고 기존 Python fallback 사용 |
| `dist/index.js:47685` 이후 exports | parse·compare/diffBlocks·patch·fill·validate·render 등 공개 API 확인. setup/watch는 root export에 없음 | 필요한 라이브러리 API만 명시적으로 호출 |
| `dist/chunk-F4KJAHPS.js:26` 및 `:49` | ZIP path traversal 검증 및 ZIP 엔트리/압축 해제 상한 코드 확인 | 어댑터 자체 입력 크기·출력 크기·시간제한도 유지 |

실행 텍스트 72개와 JSON/README에 위험 패턴 검색을 적용하고 위 경로를 수동으로
추적했다. `eval`, `new Function`, 임의 shell 문자열 실행, SSH/AWS 자격증명 접근,
MEMORY/SOUL/AGENTS 접근, 브라우저 쿠키 수집, cron/systemd 등록 패턴은 해당 검색에서
발견하지 못했다. 정규식의 `.exec()`는 일반 문서 파싱이며 shell 실행과 구분했다.
번들 JS는 들여쓰기와 source map을 가진 빌드 산출물이며 일부 한국어 Unicode escape는
빌드 표현이다. 이 사실만으로 악성 은닉으로 판정하지 않았다. 직접 배포물에 native
실행 바이너리/wasm은 없고 HWPX 2개는 문서 템플릿이다.

## 설치 진행 조건

1. 프로젝트 전용 경로에만 `kordoc@4.21.30`을 설치한다. 전역 설치·기존 MCP 설치 경로 변경 금지.
2. `--ignore-scripts --omit=optional`을 유지한다. optional `sharp`, `onnxruntime-node`, `@hyzyla/pdfium`, `@huggingface/transformers` 및 OCR 모델은 이번 기본 설치에서 제외한다.
3. 생성 lockfile의 정확한 버전·integrity를 보존하고 설치 후 dependency audit를 별도로 확인한다. 이 보고서는 전이 의존성 전수 코드 심사를 대신하지 않는다.
4. adapter child process에 `KORDOC_OFFLINE=1`, `ocr:false`, `formulaOcr:false`를 적용하고 사용자 입력 파일을 읽은 Buffer를 넘긴다. raw CLI/setup/watch와 `filePath` 전달을 허용하지 않는다.
5. 출력은 새 파일로 기록하고 원본 덮어쓰기를 거부한다. 기존 Python/Hancom 변환·검증 경로를 유지하며 회귀 시험 후 기능 사용을 확인한다.
6. 신규 입력 처리에는 크기 제한, timeout/cancel 및 반환 JSON 검증을 적용한다. 악성 문서 파서 공격·자원 고갈 위험은 정적 검색만으로 배제되지 않는다.

## 증거 파일

- `out/kordoc-security/npm-metadata-verified.json`
- `out/kordoc-security/kordoc-4.21.30.tgz`
- `out/kordoc-security/integrity.json`
- `out/kordoc-security/pack-manifest.json` — 파일별 이름·크기·mode
- `out/kordoc-security/file-inventory.txt` — 전체 파일 목록
- `out/kordoc-security/static-hits.txt`, `secondary-hits.txt` — 1차·2차 정적 검색 결과(정규식 false positive 포함)

기본 sandbox의 첫 npm 조회는 DNS `ENOTFOUND`로 실패했다. 설치 전 읽기/다운로드만
권한 확장으로 재시도하여 성공했으며 설정 변경은 수행하지 않았다. 실패 조회의
`npm-metadata.json`은 증거 원본으로 사용하지 않고 성공한 `npm-metadata-verified.json`을 사용한다.

## 추가 심사: PDF 비교용 pdfjs-dist 4.10.38

```text
════════════════════════════════════
  SKILL / MCP SECURITY ASSESSMENT
────────────────────────────────────
  Name:         pdfjs-dist
  Version:      4.10.38
  Source:       npm registry; github.com/mozilla/pdf.js
  Author:       Mozilla PDF.js project (package repository metadata)
  Trust Tier:   1 — official project distribution
  Published:    2025-01-01 22:41:09 KST (registry)
  Last Updated: version pinned; not asserted to be current/latest
────────────────────────────────────
  FILES SCANNED
  Total: 355 inventoried | Executable text: 19 MJS
  Others: 10 maps, 81 declarations, 182 font/CMap assets,
    63 docs/styles/images/JSON/misc
  High-risk files: legacy/build/pdf.mjs, pdf.worker.mjs,
    sandbox/viewer bundles; optional native canvas dependency
────────────────────────────────────
  RED FLAGS
  • MEDIUM: library supports URL fetching and dynamic function compilation.
    The kordoc call uses local Uint8Array data and isEvalSupported:false.
  • MEDIUM: optional @napi-rs/canvas includes native components.
    Exclude with --omit=optional; no native canvas package was audited here.
  • MEDIUM: minified/sandbox bundles are build artifacts; they were not
    fully deobfuscated or audited. Do not invoke the viewer/scripting sandbox.
────────────────────────────────────
  PERMISSIONS REQUIRED
  Read:     selected input buffer and local cmaps/standard_fonts assets
  Write:    no PDF.js output write needed; adapter manages explicit outputs
  Network:  npm during install; no URL input or remote asset path in adapter
  System:   Node module loading; no package install hooks
  Env Vars: no credential access found in the inspected parsing path
────────────────────────────────────
  ARCHITECTURE
  Credential handling: no application API keys required
  Human-in-the-loop: scoped dependency install authorized with main task
  Auto-update: none in inspected parsing call; pin via project lockfile
  Data boundary: local data buffer and package-local font/CMap assets
  Degradation: missing optional canvas can limit image rendering; verify parsing
────────────────────────────────────
  RISK:     MEDIUM
  VERDICT:  CAUTION — scoped non-OCR PDF parsing installation may proceed
────────────────────────────────────
  NOTES
  Limited static review, not a complete PDF.js/security-advisory audit.
  Package code was downloaded and read, never imported or executed here.
════════════════════════════════════
```

- [PDF.js 공식 프로젝트](https://github.com/mozilla/pdf.js), [고정 tarball](https://registry.npmjs.org/pdfjs-dist/-/pdfjs-dist-4.10.38.tgz).
- 라이선스 Apache-2.0, Node >=20. `package.json`의 scripts는 `{}`이고 필수 dependencies는 없다. 유일한 optional dependency는 `@napi-rs/canvas:^0.1.65`이다.
- 파일 유형: `.mjs` 19, `.map` 10, `.mts` 3, `.ts` 78, `.bcmap` 168, `.pfb` 10, `.ttf` 4, `.svg` 52, `.gif` 2, `.css` 2, `.json` 1, `.md` 2, 확장자 없음 4. CMap/폰트는 바이너리 데이터이며 네이티브 실행 파일로 분류하지 않았다. sandbox 빌드 내부의 컴파일 산출물까지 전수 분석하지 않았다.
- 비압축 37,350,025 bytes / 355 files. 전체 tar 경로 안전성 확인 및 registry SRI와 직접 SHA-512 계산 일치.
- SHA-256: `1011b38553532d7078c59f26b15a471f8dae00f101b60e2add9b8511737a1ce0`.
- SRI: `sha512-/Y3fcFrXEAsMjJXeL9J8+ZG9U01LbuWaYypvDW2ycW1jL269L3js3DVBjDJ0Up9Np1uqDXsDrRihHANhZOlwdQ==`.
- kordoc `dist/parser-X4GWGZY2.js:3366-3403`은 local package의 `cmaps`/`standard_fonts` 경로, `isEvalSupported:false`, `getDocument({data:new Uint8Array(...)})`, 30초 로딩 제한을 사용한다. 다운로드 URL을 getDocument에 넘기는 경로가 아니다.
- PDF.js `legacy/build/pdf.worker.mjs:32232`의 `new Function(...compiled)` 경로는 `isEvalSupported`를 확인한다. 빈 문자열로 지원 여부를 확인하는 feature probe는 별도이며 악성 문서 코드 실행으로 곧바로 해석하지 않았다.
- PDF.js `legacy/build/pdf.mjs:11416`은 optional canvas를 시도하고 부재 시 경고한다. 따라서 설치 성공만으로 SVG/이미지 렌더나 모든 PDF 파싱이 성공한다고 볼 수 없으며 fixture로 실제 텍스트·표 비교를 검증해야 한다.
- 허용 설치 조건: 프로젝트에 `pdfjs-dist:4.10.38`을 직접 exact dependency로 기록하고 `--ignore-scripts --omit=optional`을 유지한다. `@napi-rs/canvas`, OCR, 이미지 렌더, viewer/sandbox는 추가하지 않는다. 기존 Python PDF 변환 fallback을 유지한다.
- 증거: `out/kordoc-security/pdfjs-metadata.json`, `pdfjs-pack-manifest.json`, `pdfjs-file-inventory.txt`, `pdfjs-integrity.json`, `pdfjs-dist-4.10.38.tgz`.
