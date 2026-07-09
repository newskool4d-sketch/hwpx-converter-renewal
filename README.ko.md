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
- 텍스트 PDF: `pdfplumber`, `PyMuPDF` 등 PDF 텍스트 라이브러리 (실행 파일에 번들 포함)
- 스캔 이미지 PDF: `kordoc-ai` 등 OCR 도구

PDF 지원은 두 단계로 나뉩니다:

- 텍스트 PDF: Python PDF 라이브러리로 내장 텍스트를 추출합니다.
- 스캔 이미지 PDF: OCR이 필요합니다. `--kordoc-home` 옵션 또는 `KORDOC_HOME` 환경변수로 OCR 경로를 지정합니다.

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

### GUI 실행 파일 빌드

```powershell
python -m PyInstaller --clean .\anyway_to_hwpx_gui.spec
```

spec 기본값은 `HWPX_GUI_PDF_STACK=full`로, 구조화 PDF 추출 경로와 텍스트 PDF 폴백 라이브러리를 함께 번들합니다. PDF 스택 일부를 제외해 더 작게 빌드할 수 있습니다:

```powershell
$env:HWPX_GUI_PDF_STACK = "text"
python -m PyInstaller --clean .\anyway_to_hwpx_gui.spec

$env:HWPX_GUI_PDF_STACK = "none"
python -m PyInstaller --clean .\anyway_to_hwpx_gui.spec
```

배포 전 PyInstaller 경고, 특히 선택적 PDF/OCR 모듈 관련 경고를 확인하세요.
