# HWPX Converter Renewal

[English](README.md) | **한국어**

Markdown, TXT, DOCX, HTML, CSV, XLSX, PDF 파일을 한컴 HWP COM 자동화를 통해 HWPX로 변환합니다.

## 다운로드

[최신 릴리스](https://github.com/newskool4d-sketch/hwpx-converter-renewal/releases/latest)에서 GUI 실행 파일을 내려받을 수 있습니다:

- **`anyway_to_hwpx_gui.exe`** — 설치 불필요 (Windows 64bit, 한컴오피스 한글 설치 필수)

내려받아 실행한 뒤 원본 파일 선택 → 저장 폴더 지정 → 변환 시작 순서로 사용하면 됩니다.

## 사용자 안내

### 요구 사항

- Windows
- 한컴오피스 한글(HWP) 설치
- `HWPFrame.HwpObject` COM 자동화 동작
- PDF 입력: 아래 표의 `full` 또는 `text` 스택으로 빌드
- 스캔 이미지 PDF: `kordoc-ai` 등 OCR 도구 (OCR은 실행 파일에 포함하지 않음)

PDF 지원은 두 단계로 나뉩니다:

- **레이아웃**: PyMuPDF로 각 페이지를 200 DPI RGB 이미지로 렌더링합니다. 페이지 모양은 보존되지만 삽입된 페이지는 편집 가능한 텍스트가 아닙니다.
- **편집 가능**: 텍스트·표를 HWP 문단·표로 추출합니다. 검색·편집이 가능하지만 복잡한 위치·글꼴·스캔 페이지 모양은 정확히 재현되지 않을 수 있습니다. 스캔 PDF에는 여전히 OCR이 필요합니다.

편집 가능 모드의 기본값은 줄간격 160%, 문단 아래 간격 2, 장평·자간 기본값, 한국어 명사+조사 줄바꿈 보호입니다. HWPX XML 직접 입력이나 클라우드 OCR 서비스는 사용하지 않습니다.

`full` 스택은 Java 11 이상에서 `opendataloader-pdf`를 편집 추출에 우선 사용합니다. Java가 없거나 버전이 낮으면 GUI가 진단 문구를 남기고, 설치된 `pdfplumber`·PyMuPDF·pypdf가 있으면 로컬 편집 가능 폴백을 사용합니다. 다음 명령으로 Java를 확인할 수 있습니다:

```powershell
java -version
```

ODL 경로에는 Java 11 이상이 필요하며, `text` 폴백 경로에는 Java가 필요하지 않습니다.

### GUI 사용법

로컬 빌드가 있으면 GUI 실행 파일을 실행합니다:

```text
dist\anyway_to_hwpx_gui.exe
```

원본 파일을 선택하고 저장 폴더를 지정한 뒤 변환을 시작합니다. "저장 폴더 비우기(앱 관리 파일만)" 옵션을 켜면 이전 실행에서 앱 매니페스트에 기록된 파일만 정리합니다.

기존 HWPX 파일은 덮어쓰지 않습니다. 같은 이름이 있으면 ` - 2`, ` - 3` 형식으로 이름을 붙입니다.

### CLI 사용법

변환 전에 HWP COM 자동화가 동작하는지 확인합니다:

```powershell
python anyway_to_hwpx_com.py --preflight
```

파일 1개 변환:

```powershell
python anyway_to_hwpx_com.py "input.md" -o "C:\output"
```

"끝" 표시 삽입 옵션과 함께 변환:

```powershell
python anyway_to_hwpx_com.py "input.md" -o "C:\output" --insert-end-mark
```

앱 관리 출력 폴더를 빈 폴더로 재사용:

```powershell
python anyway_to_hwpx_com.py "input.md" -o "C:\output" --empty-output-folder
```

`--empty-output-folder`는 폴더에 이 앱의 매니페스트가 있고 기존 파일이 모두 매니페스트에 기록된 경우가 아니면 비어 있지 않은 폴더를 거부합니다.

스캔 PDF용 OCR 경로를 직접 지정:

```powershell
python anyway_to_hwpx_com.py "scan.pdf" -o "C:\output" --kordoc-home "C:\tools\kordoc-ai"
```

또는 환경변수로 지정:

```powershell
$env:KORDOC_HOME = "C:\tools\kordoc-ai"
python anyway_to_hwpx_com.py "scan.pdf" -o "C:\output"
```

지원 입력 형식 목록 확인:

```powershell
python anyway_to_hwpx_com.py --list-formats
```

## 개발자 안내

### 파일 구성

- `anyway_to_hwpx_com.py`: CLI 변환 엔진
- `anyway_to_hwpx_gui.py`: Tkinter GUI 래퍼
- `requirements.txt`: 개발·재빌드용 Python 의존성
- `samples/`: 소형 샘플 입력 파일
- `tests/`: COM 없이 실행되는 파서·표 레이아웃·출력 경로·OCR 경로 테스트
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

### 테스트

한컴 HWP 없이 실행 가능한 테스트:

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
  --distpath "$root\dist" --workpath "$root\work" --specpath (Get-Location) `
  .\anyway_to_hwpx_gui.spec
```

빌드하지 않고 세 스택의 소스·의존성만 확인:

```powershell
.\scripts\packaging_smoke.ps1
```

헬퍼로 격리 빌드를 실행하려면 `.\scripts\packaging_smoke.ps1 -Build`를 사용합니다. 기존 `C:\tmp\hwpx-gui-<stack>` 폴더를 덮어쓰지 않으며, 성공으로 보고된 빌드에 `anyway_to_hwpx_gui.exe`가 실제로 생성됐는지도 확인합니다.

spec은 `tkinterdnd2`의 데이터·네이티브 바이너리·hidden import를 명시적으로 수집합니다. 실행 시 이 패키지가 없으면 표준 파일 선택기로 자동 전환하며 드래그 앤 드롭만 사용할 수 없습니다. 레이아웃 경로는 PyMuPDF의 `Pixmap.tobytes("png")` 직접 저장을 유지하므로 Pillow(PIL)는 의도적으로 제외합니다.

배포 전 PyInstaller 경고, 특히 선택적 PDF/OCR 모듈 관련 경고를 확인하세요. PyInstaller 종료 코드 0만으로 성공을 판단하지 말고, 지정한 `C:\tmp` dist 경로의 실행 파일과 경고 로그를 함께 확인합니다.
