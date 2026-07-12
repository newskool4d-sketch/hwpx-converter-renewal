---
slug: pdf-fidelity-dnd
status: planned
intent: clear
review_required: true
pending-action: await user choice to start execution or request high-accuracy review
approach: PDF의 원본 레이아웃 보존 모드와 기존 편집 모드를 분리하고, 파일 목록 영역의 OS 파일 드롭 및 IBM Carbon 기반 4색 기능 상태 UI 재설계를 한 계획으로 수행한다.
---

# Draft: pdf-fidelity-dnd

## Components (topology ledger)
<!-- Lock the SHAPE before depth. One row per top-level component that can succeed or fail independently. -->
<!-- id | outcome (one line) | status: active|deferred | evidence path -->
| PDF-FIDELITY | PDF 페이지를 1:1 이미지로 HWPX에 넣는 원본 레이아웃 보존 경로 | active | anyway_to_hwpx_com.py:1397-1423, 2307-2400 |
| PDF-EDITABLE | 기존 ODL→pdfplumber→OCR/텍스트 폴백의 수정 가능 구조 파싱 경로 | active | anyway_to_hwpx_com.py:1120-1423 |
| FILE-DROP | 파일 목록 영역(비어 있을 때 포함)의 다중 OS 파일 드롭과 안전한 목록 추가 | active | anyway_to_hwpx_gui.py:141-173, 249-261 |
| UI-REDESIGN | PDF 방식·드롭·진행/오류 상태를 포함한 Tkinter 화면 설계 체계화 | active | anyway_to_hwpx_gui.py:27-115, 124-246; gui_preview.png; DESIGN-ibm.md |
| PACKAGING-QA | 추가 런타임·PyInstaller·HWP COM 검증과 사용자 진단 | active | requirements.txt, anyway_to_hwpx_gui.spec:1-76, tests/ |

## Open assumptions (announced defaults)
<!-- Record any default you adopt instead of asking, so the user can veto it at the gate. -->
<!-- assumption | adopted default | rationale | reversible? -->
| PDF 기본 모드 | 원본 레이아웃 우선, 편집 우선은 명시 선택 | 사용자가 승인한 방향이며 PDF 블록 재조립의 구조적 한계를 해소 | yes |
| 레이아웃 모드 범위 | PyMuPDF 200 DPI 페이지 이미지, 텍스트 오버레이·자동 클라우드 OCR 제외 | 시각 충실도와 개인정보 보호를 우선하고 구현 범위를 통제 | yes |
| 스캔 PDF | 레이아웃 모드에서는 OCR 없이 이미지 보존, 편집 모드에서는 기존 KORDOC 경로와 진단만 유지 | 신규 외부 OCR 서비스·비용을 도입하지 않음 | yes |
| 파일 드롭 기술 | tkinterdnd2를 PyInstaller에 포함하고, 패키지 미포함 개발 환경에서는 파일 선택 기능을 계속 제공 | 표준 Tkinter는 외부 파일 드롭을 제공하지 않음 | yes |
| 테스트 | Python unittest 기반 TDD, GUI는 순수 입력 정규화 로직을 분리해 headless로 시험 | 기존 test suite가 unittest이며 GUI 테스트가 없음 | yes |
| PDF 기본 적용 범위 | GUI·CLI·`convert_file()` 모두 `layout` 기본값, `--pdf-mode editable`로 명시 전환 | 사용자가 승인한 “원본 레이아웃 우선”을 호출 경로별로 다르게 해석하지 않음 | yes |
| 레이아웃 모드 COM 경로 | HWP COM의 그림 삽입만 사용하고 HWPX ZIP을 직접 조립·수정하지 않음 | 기존 생성 경로를 보존하고 HWPX 이미지 XML 수작업 손상 위험을 피함 | yes |
| 레이아웃 모드 후처리 | 페이지 여백·표·목록·단락 XML 후처리를 전부 건너뜀 | 이미지 페이지의 원래 기하를 사후 공문서 서식 규칙으로 변형하지 않음 | yes |
| PDF 선택 단위 | 현재 파일 목록 모델을 유지해 한 번의 변환 작업에서 모든 PDF에 하나의 전역 모드를 적용 | 파일별 옵션 모델을 새로 도입하지 않아 목록·진행 제어 복잡도를 억제 | yes |
| DnD 잠금 | 변환 시작 시 파일 추가/삭제/비우기·저장 폴더·옵션·PDF 모드 컨트롤을 비활성화하고 worker에는 파일 목록 사본을 전달 | worker가 가변 리스트를 직접 순회하는 레이스를 제거 | yes |
| 큰 PDF 보호 | 200 DPI PNG를 임시 폴더에 순차 저장하고, 렌더 자산 합계가 500 MiB를 넘으면 중단·삭제·편집 모드 안내 | 실행 중 메모리/디스크 폭주를 방지 | yes |
| ODL Java 진단 | `java -version`을 5초 내 실행해 11+ 여부를 노트로 남기며, 실패는 ODL 기능만 비활성화하고 pdfplumber 폴백은 유지 | 기존 broad exception을 사용자 조치 안내로 바꿈 | yes |
| UI 시각 기준 | `DESIGN-ibm.md`의 Carbon 계열: IBM Blue·성공 Green·경고 Yellow·오류 Red를 기능 상태에 사용하고, 흰색/회색/차콜은 구조 색으로 사용 | 사용자가 IBM 및 3색 이상 사용을 명시함. 색은 장식이 아니라 상태·행동에만 배정 | yes |

## Findings (cited - path:lines)
- `parse_pdf`는 ODL 실패 시 pdfplumber, 이후 OCR/텍스트 추출 결과를 Markdown 블록으로 재파싱한다. 좌표·글꼴·그림·페이지 기하 정보는 HWPX 빌드까지 전달되지 않는다: `anyway_to_hwpx_com.py:1397-1423`.
- ODL 변환은 이미지·머리말·꼬리말을 현재 무시한다: `anyway_to_hwpx_com.py:731-768`.
- `build_doc`가 처리하는 블록은 텍스트·표 계열뿐이며 이미지/페이지 블록과 그림 삽입 COM 헬퍼가 없다: `anyway_to_hwpx_com.py:1709-1716`, `2307-2400`.
- GUI 파일 목록은 `Listbox`와 파일 선택 대화상자만 사용하며, 드롭 대상·드롭 이벤트가 없다: `anyway_to_hwpx_gui.py:141-173`, `249-261`.
- 파일 목록 카드와 저장 설정·진행 로그의 색/공간값은 한 파일에 하드코딩되어 있고, 프로젝트의 `DESIGN.md`는 없다: `anyway_to_hwpx_gui.py:27-115`; repository root search.
- PyInstaller는 ODL/PDF 모듈의 hidden import와 JAR를 조건부로 수집하지만 `requirements.txt`에는 ODL·DnD 의존성이 없다: `anyway_to_hwpx_gui.spec:1-76`, `requirements.txt:1-8`.
- 현재 무GUI 단위 테스트는 `python -m unittest discover -s tests`로 159건 통과했으며 GUI 동작 테스트는 없다.
- 외부 근거: ODL의 구조 추출은 Java 11+를 요구하고, PyMuPDF `Page.get_pixmap()`은 페이지 렌더링을 지원하며, tkinterdnd2는 Tcl 리스트를 `splitlist`로 해석하는 파일 드롭 API를 제공한다.
- 사용자가 지정한 디자인 자료는 `C:\Users\홍주형\OneDrive - 인천광역시교육청\바탕 화면\디자인 md\`에 존재한다. 현재 앱과 가장 가까운 업무용 후보는 `DESIGN-ibm.md`, 온화한 크림 계열 후보는 `DESIGN-airbnb.md`, 절제된 최소주의 후보는 `DESIGN-apple.md`다.
- 계획 검토에서 추가 확인된 위험: 기존 `convert_file`은 모든 출력에 공문서 XML 후처리를 적용하고(`anyway_to_hwpx_com.py:2729-2734`), worker는 가변 `self.files`를 직접 순회한다(`anyway_to_hwpx_gui.py:314-323`). 레이아웃 모드와 DnD에는 각각 후처리 분기·작업 목록 snapshot이 필요하다.

## Decisions (with rationale)
- PDF 변환은 `layout`(기본)과 `editable` 두 모드를 제공한다. `layout`은 PDF 페이지를 그림으로 넣어 원본 레이아웃을 보존하되 편집 가능한 텍스트를 제공하지 않는다. `editable`은 현 구조 파서를 유지·보강한다.
- 파일 목록의 실제 `Listbox`와 그 빈 상태를 감싸는 목록 컨테이너를 드롭 타깃으로 등록한다. 헤더 버튼·저장 폴더 입력칸은 드롭 타깃에 포함하지 않는다.
- 드롭·파일 선택은 하나의 입력 정규화 함수(실재 파일·지원 확장자·중복 제거·변환 중 거부·저장 폴더 기본값)로 합친다.
- UI 재설계는 기존 Tkinter/ttk 스택을 유지한다. 웹 프레임워크·클라우드 업로드·별도 설치형 앱으로 전환하지 않는다.
- 디자인 기준은 사용자 선택에 따라 `C:\Users\홍주형\OneDrive - 인천광역시교육청\바탕 화면\디자인 md\DESIGN-ibm.md`다. 0px/2px 중심의 평면 사각형, 1px 헤어라인, IBM Plex Sans 우선(미설치 시 맑은 고딕 폴백), 4px 간격 단위를 `DESIGN.md`에 기록한다.
- 색 사용은 IBM Blue `#0F62FE`(주 행동·포커스·정보), Success Green `#24A148`(완료), Warning Yellow `#F1C21B`(주의·드롭 경고), Error Red `#DA1E28`(실패·거부)의 네 가지 유채색 기능 토큰으로 고정한다. 카드·배경은 흰색/회색/차콜 중성색만 사용한다.
- 레이아웃 모드는 HWP COM 그림 삽입 경로를 새로 추가하고, 동일 크기의 PDF 페이지에 한해 원본 페이지 기하를 적용한다. 혼합 크기/방향 PDF는 변환 전단에서 명확히 거부하고 편집 모드를 안내한다.
- 진단은 GUI의 선택 모드 설명·상태줄·진행 로그와 CLI conversion note에 동일한 문구로 노출한다. 모달은 실행을 막는 오류(암호화, 혼합 페이지 크기, 자산 용량 한도)에서만 쓴다.

## Scope IN
- PDF 원본 레이아웃 우선 이미지 모드, 편집 우선 구조 파싱 모드, 명시적 CLI/GUI 선택과 진단
- 목록 영역 드롭, 파일 선택과의 일관된 다중 파일 처리, 드롭 상태 피드백
- 제공된 디자인 자료 한 종을 기준으로 한 `DESIGN.md`, Tkinter 토큰/컴포넌트/상태 재설계
- 의존성·PyInstaller·문서·자동/COM 검증

## Scope OUT (Must NOT have)
- PDF에서 편집 가능한 텍스트와 픽셀 단위 원본 레이아웃을 동시에 보장하는 텍스트 오버레이
- 새로운 클라우드 OCR·PDF SaaS·개인정보 외부 전송
- 기존 입력 원본, 기존 HWPX 출력, 사용자의 더티 워크트리 파일 삭제·수정
- 파일 목록 외의 임의 창/입력칸을 드롭 타깃으로 확대

## Open questions
- 없음. 사용자 선택과 검토 결과로 범위·방식·검증 전략이 확정되었다.

## Approval gate
status: approved 2026-07-10
completed action: wrote `.omo/plans/pdf-fidelity-dnd.md` only; product code remains unchanged
brief: PDF 기본 layout/선택 editable, file-list-area DnD, IBM Carbon UI with four functional chromatic colors, dependency/package/COM verification
<!-- When exploration is exhausted and unknowns are answered, set status: awaiting-approval. -->
<!-- That durable record is the loop guard: on a later turn read it and resume at the gate instead of re-running exploration. -->

## High-accuracy review
status: blocked-by-independent-cli-network
requested: 2026-07-10
native-momus: "Pass 1 ITERATE (3 findings); Pass 2 OKAY — /root/momus_high_accuracy_retry. Verified current plan against repository and all listed fixes."
independent-codex-cli: "Pass 1 ITERATE (10 findings) in isolated C:\\tmp workspace/CODEX_HOME; fixes applied. Pass 2 attempted three ways with gpt-5.5/xhigh/read-only but failed before verdict: WebSocket and HTTPS transport both returned Windows socket error 10013 (access denied)."
fix-retry-summary: "Applied all Pass 1 findings: full/text/none capability matrix; exact six-postprocessor guard; empirical Hancom PageSetup/InsertPicture/BreakPage contract and geometry/pixel assertions; dependency prerequisite and pins; convert_file-owned temp lifetime; guarded BaseTk, central busy lock, immutable worker snapshots; scripted 21-state GUI capture and HWPX/PDF geometry-pixel roundtrip; noninteractive isolated-stack PyInstaller commands; Git-root/dirty baseline; semantic-color reverse mapping. Native review passed. Independent CLI final approval remains unverified due environment network restriction."
