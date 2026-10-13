# 문서 도구 사용 안내

기존 변환 화면의 **문서 도구**에서 읽기, 비교, 구조 검사, 양식 채우기, 서식 보존 수정, 미리보기를 사용할 수 있습니다. 기존 파일 변환의 기본 엔진과 공문 서식은 유지합니다.

## 설치

Node.js 20 이상이 설치된 Windows에서 프로젝트 루트의 다음 스크립트를 실행합니다.

```powershell
.\scripts\install_kordoc.ps1
```

프로젝트 `deps/kordoc`에 `kordoc 4.21.30`과 `pdfjs-dist 4.10.38`을 고정 설치합니다. lockfile이 있으면 `npm ci`를 사용합니다. lifecycle script와 선택 의존성은 제외하며 기존 MCP 설정·패키지를 변경하지 않습니다. 배포 EXE에서는 실행 파일 옆 `deps/kordoc/node_modules`가 필요합니다.

별도 패키지 위치는 `HWPX_KORDOC_HOME`, Node 실행 경로는 `HWPX_NODE_PATH`로 지정할 수 있습니다. 앱은 설치·업데이트를 자동 실행하지 않습니다. Node 또는 kordoc이 없으면 문서 도구에 설명이 표시되고 기존 변환은 사용할 수 있습니다.

## 화면에서 사용하는 순서

1. **읽기**: 원본을 선택하고 본문·표 정보를 확인합니다. 필요하면 Markdown으로 저장합니다.
2. **비교**: 원본과 비교 문서를 선택합니다. 문단·표 셀, 숫자·병합·이미지 차이를 확인합니다. 차이 자체가 오류라는 뜻은 아닙니다.
3. **양식 채우기**: 필드를 확인하고 라벨과 값이 들어 있는 JSON 파일을 불러옵니다. 먼저 결과를 확인한 다음 새 HWPX 사본으로 저장합니다.
4. **본문 수정**: 읽기에서 저장한 Markdown을 편집해 불러옵니다. 먼저 적용 결과를 확인한 다음 별도 파일로 저장합니다.
5. **미리보기**: 페이지를 이동하며 브라우저에서 확대·축소합니다. 실제 한컴 화면·인쇄와 다를 수 있습니다.
6. **서식·표기 검사**: 견본 서식 프로필을 추출하거나 공문 표기 검사 결과를 봅니다. 견본 서식은 기관 규칙에 자동 덮어쓰지 않습니다.

미리보기 이후 입력이 바뀌면 다시 미리 확인해야 합니다. 중복 라벨·지원하지 않는 변경이 남으면 부분 결과와 사유가 표시되며 사본 저장을 막습니다. 수정본은 원본과 다른 새 파일로만 저장합니다. GUI 보고서·Markdown은 저장 대화상자의 덮어쓰기 확인을 따릅니다. 문서 내용이 포함될 수 있으므로 저장 위치를 확인하세요.

양식 값 예시: `{"사업명": "생태 체험", "참가 인원": "30명"}`

## 변환 취소·재시도

기존 변환 화면에서 파일별 제한 시간과 취소·실패 재시도를 사용할 수 있습니다. 파일마다 별도 Python 프로세스에서 처리합니다. 성공한 출력은 유지하며 실패·미처리 파일만 재시도합니다. 취소·timeout 때 최대 2초 동안 정상 종료를 기다린 다음 앱의 작업 프로세스만 종료합니다. 사용자 한글 프로세스를 일괄 종료하지 않습니다. 한글 자체가 응답하지 않으면 남은 창 안내를 확인하세요.

## 자동화 명령

`python`은 프로젝트 의존성이 설치된 Python을 뜻합니다. 새 문서 명령은 한컴 없이 실행할 수 있습니다.

```powershell
python document_cli.py diagnose
python document_cli.py parse "원본.hwpx" --report "읽기.json"
python document_cli.py compare "원본.hwpx" "수정본.hwpx" --report "비교.json"
python document_cli.py validate "원본.hwpx"
python document_cli.py fields "양식.hwpx"
python document_cli.py fill "양식.hwpx" --values-file "값.json"
python document_cli.py fill "양식.hwpx" --values-file "값.json" --apply --output "작성본.hwpx"
python document_cli.py patch "원본.hwpx" --markdown-file "수정.md"
python document_cli.py patch "원본.hwpx" --markdown-file "수정.md" --apply --output "수정본.hwpx"
python document_cli.py render "원본.hwpx" --page 1 --report "미리보기.json"
python document_cli.py profile "견본.hwpx" --report "서식.json"
python document_cli.py lint "원본.hwpx"
```

응답은 `ok/status/action/data/warnings/error`가 있는 JSON입니다. 종료 코드는 성공 0, 오류 1, 부분 결과 2, 취소 130입니다. fill/patch는 `--apply`가 없으면 미리보기입니다. render JSON에는 SVG가 포함됩니다.

원본 텍스트·표를 기관 서식으로 새로 변환하는 선택 입력 엔진도 제공합니다. 원본 레이아웃 보존 편집과는 다른 기능입니다.

```powershell
python anyway_to_hwpx_com.py "원본.hwpx" --input-engine kordoc -o "새출력"
python scripts\compare_pdf_engines.py "문서.pdf" --report "PDF비교.json"
```

PDF 비교는 로컬 pdfplumber와 kordoc의 OCR 없는 추출을 대상으로 합니다. `--reference "검토한정답.txt"`를 주면 토큰 재현율·정밀도를 기록합니다. 엔진 간 일치도는 정확도가 아니며 읽기 순서·표 구조·시각 재현은 별도 검토합니다. 기본 PDF 엔진은 변경하지 않습니다.

## 지원 범위

- 선택 엔진의 새 변환 입력: HWP/HWPX/HWPML/XLS/XLSX/DOCX/PPTX/PDF. 원본 수정·양식·구조 검사·견본 서식은 HWPX 우선입니다.
- Markdown 단독 로컬 이미지와 DOCX 본문 이미지 삽입을 지원합니다. 표 내부 이미지·중첩표·일부 원본 서식에는 제한이 있으며 경고를 확인해야 합니다.
- 하이퍼링크는 표시 텍스트를 유지합니다. 클릭 가능한 링크와 원본 강조 서식의 완전 보존은 제공하지 않습니다.
- 새 연결은 오프라인입니다. OCR·수식 모델 다운로드, 웹 이미지 다운로드, watch 웹훅, MCP 자동 등록, Chromium PDF 인쇄는 사용하지 않습니다. 기존 별도 OCR 경로는 유지합니다.
- 구조 검사 성공, 내용 비교 성공, 실제 한컴 확인은 별도 검증입니다.

보안 근거: [설치 전 심사](kordoc-security-review.md).
