# HWPX Converter Renewal

[English](README.md) | **한국어**

Markdown, TXT, DOCX, HTML, CSV, XLSX, PDF를 **한컴 서식의 HWPX로 변환**하는 Windows 앱입니다. 선택형 로컬 문서 도구로 기존 HWP/HWPX를 읽고, 비교하고, HWPX 수정본과 작성한 양식 사본을 만들 수 있습니다.

[최신 릴리스](https://github.com/newskool4d-sketch/hwpx-converter-renewal/releases/latest) · [문서 도구 상세 안내](docs/document-tools.md) · [2026.10.13 변경 내용](https://github.com/newskool4d-sketch/hwpx-converter-renewal/releases/tag/v2026.10.13)

## 다운로드

| 필요한 기능 | 다운로드 | 사용 조건 |
| --- | --- | --- |
| 변환 + 문서 읽기·비교·수정 **(권장)** | [Windows 전체 ZIP](https://github.com/newskool4d-sketch/hwpx-converter-renewal/releases/download/v2026.10.13/hwpx-converter-v2026.10.13-windows-x64.zip) | 전체 압축 해제. 문서 도구에는 Node.js 20 이상 필요 |
| 기존 파일 변환 | [EXE 단일 파일](https://github.com/newskool4d-sketch/hwpx-converter-renewal/releases/download/v2026.10.13/anyway_to_hwpx_gui.exe) | 변환에는 한컴오피스 한글 필요. 문서 도구 의존성은 미포함 |
| 파일 무결성 확인 | [SHA256SUMS.txt](https://github.com/newskool4d-sketch/hwpx-converter-renewal/releases/download/v2026.10.13/SHA256SUMS.txt) | `Get-FileHash -Algorithm SHA256 <파일>` 결과와 대조 |
| 빌드·버전 확인 | [release-manifest.json](https://github.com/newskool4d-sketch/hwpx-converter-renewal/releases/download/v2026.10.13/release-manifest.json) | 소스 커밋·빌드 구성·EXE 해시 기록 |

배포본은 `2026.10.13`, PDF `full` 스택입니다. ZIP에는 `kordoc 4.21.30`과 `pdfjs-dist 4.10.38`이 포함되며 별도 npm 설치가 필요하지 않습니다. Node.js 자체는 포함하지 않습니다.

## 빠른 시작

1. 위 ZIP을 내려받아 **폴더 전체를 압축 해제**합니다.
2. `anyway_to_hwpx_gui.exe`를 실행합니다.
3. **새 HWPX 만들기:** 원본 파일 → 저장 폴더 → 문서 유형·PDF 방식 선택 → **변환 시작**.
4. **기존 문서 다루기:** 상단 **문서 읽기 · 비교 · 수정** → 원본 선택 → 읽기·비교·양식 작업.

EXE와 `deps` 폴더를 함께 보관하세요. 이동할 때도 폴더 전체를 옮깁니다.

```text
압축 해제 폴더/
├─ anyway_to_hwpx_gui.exe
├─ deps/kordoc/node_modules/
├─ docs/document-tools.md
├─ release-manifest.json
└─ THIRD-PARTY-NOTICES.txt
```

## 주요 기능

| 기능 | 할 수 있는 일 |
| --- | --- |
| 기관 서식 변환 | 기본 7종 입력을 계획·보고 또는 시행문 유형의 HWPX로 생성, 날짜·금액 표기 정규화 |
| 읽기·비교 | 본문·표 구조 추출, Markdown 저장, 문단·셀의 내용·수치·병합 차이 확인 |
| 구조·표기 검사 | HWPX 구조 검사, 공문 표기 검사, 견본 서식 프로필 추출 |
| 수정·양식 채우기 | Markdown 본문 수정 또는 JSON 양식 값을 미리 확인한 뒤 **새 HWPX 사본** 저장 |
| 미리보기 | 페이지 이동·확대·축소, 브라우저에서 검토용 SVG 확인 |
| 변환 제어 | 파일당 제한 시간(기본 180초), 취소, **실패·미완료만 재시도** |
| 이미지 | Markdown의 단독 로컬 이미지와 DOCX 본문 이미지 삽입 |

기본 GUI 변환 입력은 **MD/TXT/DOCX/HTML/CSV/XLSX/PDF**입니다. CLI에서 `--input-engine kordoc`을 선택하면 HWP/HWPX/HWPML/XLS/XLSX/DOCX/PPTX/PDF를 읽어 새 기관 서식으로 변환할 수 있습니다. 이 선택 엔진은 기본 GUI 입력 목록과 별개입니다.

## 필요한 환경

| 용도 | 요구 사항 |
| --- | --- |
| GUI 실행 | Windows 64비트. 배포 EXE는 Python 별도 설치 불필요 |
| HWPX 변환 | 한컴오피스 한글 및 정상 동작하는 `HWPFrame.HwpObject` COM 자동화 |
| 새 문서 도구 | Node.js 20 이상 + EXE 옆 `deps/kordoc`. 문서 도구 CLI는 한컴 없이 실행 가능 |
| PDF 편집 추출 향상 | Java 11 이상(선택). 없으면 로컬 텍스트 추출로 전환 |
| 소스·CLI 실행 | 프로젝트 의존성이 설치된 Python. 아래 개발 환경 설정 참고 |

런타임 버전은 `node --version`, `java -version`으로 확인할 수 있습니다. Node 또는 문서 도구 패키지가 없어도 기존 변환은 사용할 수 있습니다.

## GUI 사용 안내

### 새 문서 변환

원본과 저장 폴더를 선택하고 **계획·보고** 또는 **시행문**을 지정합니다. 필요하면 공문 표기 정규화와 문서 끝의 `끝` 삽입을 선택합니다.

기존 HWPX는 덮어쓰지 않으며 같은 이름이 있으면 ` - 2`, ` - 3`을 붙입니다. **저장 폴더 비우기(앱 관리 파일만)**는 앱의 매니페스트로 관리되는 출력만 정리합니다.

파일당 제한 시간은 10~3,600초로 조정할 수 있습니다. 취소·시간 초과 때 최대 2초 동안 정상 종료를 기다린 뒤 앱의 작업 프로세스만 종료합니다. 성공한 출력은 유지하고 실패·미완료 파일만 재시도할 수 있습니다.

### 기존 문서 읽기·수정

상단 **문서 읽기 · 비교 · 수정**에서 원본을 선택합니다. 읽기·비교·검사 결과를 확인하거나, 수정한 Markdown·양식 값 JSON을 불러와 적용 결과를 미리 확인합니다. 양식 값의 예는 `{"사업명": "생태 체험", "참가 인원": "30명"}`입니다.

미리 확인한 뒤 입력이 달라졌거나 중복 라벨·지원하지 않는 변경이 남으면 사본 저장을 막습니다. 원본 수정·채움은 원본과 다른 새 HWPX 파일로 저장합니다. 자세한 순서는 [문서 도구 안내](docs/document-tools.md)를 참고하세요.

### PDF 방식 선택

- **레이아웃 보존(기본):** 각 페이지를 200 DPI RGB 이미지로 삽입합니다. 페이지 모양을 보존하며 글자는 편집 가능한 텍스트가 아닙니다.
- **편집 가능:** 본문·표를 HWP 문단·표로 추출합니다. 검색·편집할 수 있지만 복잡한 위치·글꼴·스캔 페이지의 정확한 재현에는 한계가 있습니다.

기본 PDF 편집 경로는 Java 11 이상에서 `opendataloader-pdf`를 우선 사용하고, 사용할 수 없으면 `pdfplumber`·PyMuPDF·pypdf로 전환합니다. 기본 서식은 줄간격 160%, 문단 아래 간격 2, 기본 장평·자간과 한국어 명사·조사 줄바꿈 보호입니다. 클라우드 OCR은 사용하지 않습니다.

## 지원 범위와 문제 해결

- **첫 실행이 느릴 때:** 단일 EXE의 임시 압축 해제가 포함됩니다. 검증 PC의 새 폴더 첫 실행은 45초를 넘겨 창이 표시됐습니다.
- **문서 도구를 사용할 수 없을 때:** `node --version`과 EXE 옆 `deps/kordoc/node_modules`를 확인하세요. 앱은 패키지를 자동 설치·업데이트하지 않습니다.
- **한글 창이 남았을 때:** 한글 자체가 응답하지 않는 경우 창이 남을 수 있습니다. 앱은 사용자 한글 프로세스를 일괄 강제 종료하지 않습니다.
- **수정·미리보기의 범위:** HWPX 수정은 지원되는 본문·셀 변경에 한합니다. SVG 미리보기와 구조 검사 성공은 실제 한컴 인쇄 확인을 대신하지 않습니다. 견본 서식은 추출하며 자동 적용하지 않습니다.
- **이미지·서식의 범위:** 표 내부 이미지·중첩표·일부 강조 서식·수식·차트에는 제한이 있습니다. 하이퍼링크는 표시 글자를 유지하며 클릭 가능한 링크의 완전 보존은 제공하지 않습니다.
- **스캔 PDF:** 레이아웃 변환은 가능하지만 글자 추출에는 별도 OCR이 필요합니다. 새 문서 도구에는 OCR 모델·모델 다운로드·웹 이미지 다운로드를 포함하지 않습니다.
- **배포 서명:** 현재 EXE에는 디지털 서명이 없습니다. 릴리스의 SHA-256 값으로 파일 무결성을 확인하세요.

## CLI 사용법

CLI 예제는 소스 체크아웃과 Python 환경에서 실행합니다. 배포 ZIP만 받은 경우에는 위 GUI를 사용하세요.

### 한컴을 통한 변환

```powershell
python anyway_to_hwpx_com.py --preflight
python anyway_to_hwpx_com.py "input.md" -o "C:\output"
python anyway_to_hwpx_com.py "input.md" -o "C:\output" --insert-end-mark
python anyway_to_hwpx_com.py --list-formats
```

앱 관리 출력 폴더를 재사용하려면 `--empty-output-folder`를 추가합니다. 비어 있지 않은 폴더는 앱 매니페스트가 있고 기존 파일 모두가 그 목록에 있을 때만 정리합니다.

선택형 kordoc 입력 엔진으로 새 기관 서식 생성:

```powershell
python anyway_to_hwpx_com.py "원본.hwpx" --input-engine kordoc -o "C:\output"
```

### 한컴 없이 문서 읽기·수정

```powershell
python document_cli.py diagnose
python document_cli.py parse "원본.hwpx" --report "읽기.json"
python document_cli.py compare "원본.hwpx" "수정본.hwpx"
python document_cli.py validate "원본.hwpx"
python document_cli.py fields "양식.hwpx"
python document_cli.py fill "양식.hwpx" --values-file "값.json"
python document_cli.py fill "양식.hwpx" --values-file "값.json" --apply --output "작성본.hwpx"
python document_cli.py patch "원본.hwpx" --markdown-file "수정.md" --apply --output "수정본.hwpx"
```

`fill`·`patch`는 `--apply`가 없으면 미리 확인만 합니다. 저장에는 `--apply --output`이 필요합니다. `--report`는 새 JSON 파일만 생성합니다. 결과는 JSON이며 종료 코드는 성공 `0`, 오류 `1`, 부분 결과 `2`, 취소 `130`입니다. `render`·`profile`·`lint`와 추가 옵션은 [전체 명령 안내](docs/document-tools.md)를 참고하세요.

### 기존 별도 OCR 연동

선택 설치한 `kordoc-ai` 경로는 새 Node 문서 도구와 별개입니다.

```powershell
python anyway_to_hwpx_com.py "scan.pdf" -o "C:\output" --kordoc-home "C:\tools\kordoc-ai"
# 같은 경로를 환경변수로 지정할 수도 있습니다.
$env:KORDOC_HOME = "C:\tools\kordoc-ai"
```

새 문서 도구의 패키지 경로는 `HWPX_KORDOC_HOME`, Node 실행 파일은 `HWPX_NODE_PATH`로 별도 지정할 수 있습니다.

## 릴리스 검증

`v2026.10.13`은 **399개 검사 통과·제외 0개**로 검증했습니다. 실제 한컴 PDF 왕복 검사, 대표 문서의 재열기·PDF 비교, 수정·양식 사본 확인, 저장소 밖 ZIP 실행·문서 읽기·정상 종료, 공개 다운로드 해시 대조를 포함합니다.

이는 검증 PC와 샘플에 대한 결과입니다. 최초 실행 지연과 지원 범위는 [릴리스 기록](https://github.com/newskool4d-sketch/hwpx-converter-renewal/releases/tag/v2026.10.13)에 명시했습니다. 이전 개발판의 상세 증거는 [구현·설치 검증 기록](docs/kordoc-implementation-verification.md)에 있습니다.

## 개발자 안내

### 파일 구성

- `anyway_to_hwpx_com.py`: CLI 변환 엔진
- `anyway_to_hwpx_gui.py`: Tkinter GUI 래퍼
- `conversion_process.py`: 파일별 작업 격리·취소·제한 시간
- `document_workbench.py` / `document_cli.py`: 문서 도구 화면·JSON CLI
- `kordoc_client.py` / `kordoc_bridge.mjs`: Python–Node 로컬 어댑터
- `deps/kordoc/package*.json`: 문서 도구의 고정 의존성·lockfile
- `requirements.txt`: 개발·재빌드용 Python 의존성
- `samples/`: 소형 샘플 입력 파일
- `tests/`: 파서·표·파일 보호·문서 도구·작업 제어 검사와 선택형 실제 COM 검사
- `verification-log.md`: 로컬 검증 이력

아래 생성물은 의도적으로 추적하지 않습니다:

- `dist/`
- `build/`
- `out/`
- `__pycache__/`

### 개발 환경 설정

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

문서 도구를 소스에서 사용하려면 Node.js 20 이상이 설치된 상태에서 실행합니다:

```powershell
.\scripts\install_kordoc.ps1
python document_cli.py diagnose
```

프로젝트 전용 경로에 고정 버전을 설치하며 기존 MCP 설정·설치본은 변경하지 않습니다. [설치 전 보안 검토](docs/kordoc-security-review.md)에서 연결 범위를 확인할 수 있습니다.

### 테스트

기본 검사(실제 COM 검사는 기본 제외, Node가 필요한 검사는 해당 실행 환경 필요):

```powershell
python -m unittest discover -s tests
```

문법 검사:

```powershell
python -m py_compile anyway_to_hwpx_com.py anyway_to_hwpx_gui.py
```

HWP COM 수동 검증은 Windows에 한컴 HWP가 설치되어 있어야 합니다:

```powershell
python anyway_to_hwpx_com.py --preflight
python anyway_to_hwpx_com.py samples\sample.md -o out
```

실제 한컴 PDF 왕복 검사도 포함하려면 작업 중인 한글 문서를 모두 닫은 뒤 실행합니다:

```powershell
$env:HWPX_RUN_COM_TESTS = "1"
python -m unittest discover -s tests
Remove-Item Env:\HWPX_RUN_COM_TESTS
```

### PDF 스택 매트릭스

spec(`HWPX_GUI_PDF_STACK`)과 실행 시 기능 진단은 다음 세 값을 동일하게 사용합니다.

| 스택 | 레이아웃 PDF | 편집 가능 PDF | ODL / Java | PDF 입력 |
| --- | --- | --- | --- | --- |
| `full` (기본) | 가능, PyMuPDF 페이지 이미지 | 가능, ODL 우선; ODL 불가 시 로컬 텍스트 폴백 | `opendataloader-pdf` 포함, Java 11+이면 ODL 활성화 | 활성화 |
| `text` | 가능, PyMuPDF 페이지 이미지 | 가능, `pdfplumber`/PyMuPDF/pypdf 폴백, ODL 미포함 | Java 불필요 | 활성화 |
| `none` | 불가 | 불가 | ODL·텍스트 스택 미포함 (공용 런타임 import는 남을 수 있음) | 변환 워커 시작 전에 비활성화 |

`layout`은 편집성보다 페이지 충실도를, `editable`은 정확한 위치보다 검색·편집 가능한 HWP 내용을 우선합니다. `none` 빌드에서는 GUI가 파일 선택기·드롭 허용 목록에서 `.pdf`를 제거하고 두 PDF 모드 컨트롤을 비활성화합니다. CLI도 렌더링이나 PDF 작업을 시작하기 전에 PDF 입력을 거부합니다.

GUI와 변환기가 모듈을 공유하므로 `none` 실행 파일에 시작에 필요한 공용 PyMuPDF import가 남을 수 있습니다. 그래도 capability 필터가 PDF 입력을 제거하고 변환기가 워커의 PDF 작업 전에 입력을 거부하므로 PDF 변환이 활성화되는 것은 아닙니다.

### GUI 실행 파일 빌드

각 스택은 `C:\tmp\hwpx-gui-<stack>` 아래에 격리된 경로를 사용하세요. PyInstaller가 저장소의 `dist\` 또는 `build\`를 건드리지 않도록 합니다:

```powershell
$stack = "full" # full, text, none 중 하나
$root = "C:\tmp\hwpx-gui-$stack"
$env:HWPX_GUI_PDF_STACK = $stack
python -m PyInstaller --clean --noconfirm `
  --distpath "$root\dist" --workpath "$root\work" `
  .\anyway_to_hwpx_gui.spec
```

빌드하지 않고 세 스택의 소스·의존성만 확인:

```powershell
.\scripts\packaging_smoke.ps1
```

헬퍼로 격리 빌드를 실행하려면 `.\scripts\packaging_smoke.ps1 -Build`를 사용합니다. 기존 `C:\tmp\hwpx-gui-<stack>` 폴더를 덮어쓰지 않으며, 성공으로 보고된 빌드에 `anyway_to_hwpx_gui.exe`가 실제로 생성됐는지도 확인합니다.

spec은 `tkinterdnd2`의 데이터·네이티브 바이너리·hidden import를 명시적으로 수집합니다. 실행 시 이 패키지가 없으면 표준 파일 선택기로 자동 전환하며 드래그 앤 드롭만 사용할 수 없습니다. 레이아웃 경로는 PyMuPDF의 `Pixmap.tobytes("png")` 직접 저장을 유지하므로 Pillow(PIL)는 의도적으로 제외합니다.

배포 전 PyInstaller 경고, 특히 선택적 PDF/OCR 모듈 관련 경고를 확인하세요. PyInstaller 종료 코드 0만으로 성공을 판단하지 말고, 지정한 `C:\tmp` dist 경로의 실행 파일과 경고 로그를 함께 확인합니다.

문서 도구 포함 배포에는 EXE 옆에 `deps/kordoc` 전체와 `docs/document-tools.md`를 함께 넣습니다. `node_modules`의 LICENSE·NOTICE·THIRD_PARTY·폰트 고지를 보존하고 Node.js 요구 사항을 안내하세요. Node 런타임과 문서 도구 패키지는 PyInstaller EXE 안에 자동 포함되지 않습니다.

### 릴리스 절차

1. `anyway_to_hwpx_com.py`의 `__version__`을 릴리스 태그 날짜(`YYYY.MM.DD`)로 갱신 — 릴리스 사이 개발 중에는 `+dev`
2. `python -m unittest discover -s tests`·`python -m py_compile anyway_to_hwpx_com.py anyway_to_hwpx_gui.py` 통과
3. 샘플 실변환 후 `python scripts/hwpx_editor_safety_gate.py <산출물>` PASS, 한글에서 열어 여백·글꼴 육안 확인
4. 격리 빌드(위 명령) 후 실행 파일 기동 확인 — 제목이 "HWPX 변환기"로 시작하는 메인 창 표시와 "Unhandled exception in script" 대화상자 부재로 판정(프로세스 생존만으로 판정 금지)
5. 전체 ZIP을 저장소 밖 새 폴더에 풀어 버전·인접 패키지 진단·읽기·정상 종료 확인
6. EXE·ZIP·빌드 manifest·SHA-256 목록을 GitHub Release에 첨부(태그는 빌드한 커밋에). 공개 다운로드 해시를 대조하며 바이너리는 저장소에 커밋하지 않음
