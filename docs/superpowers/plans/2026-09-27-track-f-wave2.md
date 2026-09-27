# Track F 웨이브 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 변환 직후 산출물 자가검증(F-2c), 문서유형·공문 정규화·"끝" 표시의 독립 선택(F-3), 버전 표기(F-1c)를 하위 호환 추가형으로 구현한다.

**Architecture:** 문서유형은 모듈 전역 bool 대신 `contextvars.ContextVar`로 바꾸고 `detect_and_parse(doc_type=…)`가 변환 1건 범위에서만 설정·복원한다(PDF 경로 포함 호출부 무변경, 전역 누수 없음). 공문 정규화는 `convert_file(official=…)`로 분리하고 `--insert-end-mark`는 정규화를 포함하는 현행 의미를 유지한다. 자가검증은 표준 라이브러리로 ZIP·XML·루트 선언·표 속성을 점검해 `[확인 필요]` note로 합류한다.

**Tech Stack:** Python 3.14 표준 라이브러리(contextvars·zipfile·xml.etree·re), unittest, Tkinter

**Spec:** `IMPROVEMENT_PLAN.md` §11-4(하류 호환 계약), §11-5 F-2c·F-3·F-1c

## Global Constraints

- CLI `files`·`-o`·`--insert-end-mark`(= 정규화 + 린트 + "끝")·`--doc-type` 현행 의미와 종료코드 0·1·2 유지
- `main`·`convert_file`·`detect_and_parse`의 기존 인자 순서·기본값 유지, 신규 인자는 키워드·기본값으로만 추가
- 신규 의존성 없음, 텍스트 자동 수정 없음(시간 표기는 린트만 — D-6)
- note 접두어 체계(웨이브 1) 유지: 린트·자가검증 문제는 `[확인 필요]`
- 한글 경로를 Bash 명령에 쓰지 않음, 실COM 검증은 사용자 폴더 하위 경로만(N16 회피)
- 커밋: `.git/TRACKF_MSG`(UTF-8) → `git commit -F`, 끝에 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`

---

### Task 1: 버전 표기 (F-1c)

**Files:** Modify `anyway_to_hwpx_com.py`(상단 상수·`main` 인자), `anyway_to_hwpx_gui.py:47`(창 제목), `README.ko.md`·`README.md`(릴리스 절차) / Test: `tests/test_conversion_notes.py`(클래스 추가), `tests/test_gui_drop_wiring.py`(소스 계약)

**Interfaces:** Produces `anyway_to_hwpx_com.__version__: str`(릴리스 시 태그 날짜 `YYYY.MM.DD`, 개발 중 `YYYY.MM.DD+dev`), CLI `--version`, GUI 제목 `HWPX 변환기 {__version__}`

- [ ] RED — 테스트

```python
class VersionTests(unittest.TestCase):
    def test_version_string_follows_release_date_scheme(self):
        self.assertRegex(converter.__version__, r"^\d{4}\.\d{2}\.\d{2}(\+dev)?$")

    def test_cli_version_prints_version_and_exits_zero(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            converter.main(["--version"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn(converter.__version__, output.getvalue())
```

GUI 소스 계약(`GuiCharacterizationTests`): `self.assertIn('self.title(f"HWPX 변환기 {converter.__version__}")', source)`

- [ ] GREEN — `__version__ = '2026.09.27+dev'`(모듈 상단), `parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')`, GUI `self.title(f"HWPX 변환기 {converter.__version__}")`
- [ ] 저장소 밖 판정 스크립트 4종(`tests/out/track-f/diag_exe_windows.py`·`smoke_exe.py`·`wait_window.py`·`close_window.py`)을 제목 **접두** 일치("HWPX 변환기")로 변경 — 정확 일치면 버전 포함 제목에서 창 미검출. `scripts/` 승격 여부는 병합 시 재질의
- [ ] README 릴리스 절차: 1단계 앞에 "`anyway_to_hwpx_com.__version__`을 릴리스 태그 날짜로 갱신(개발 중 `+dev`)" 추가, 기동 판정 문구를 "제목이 'HWPX 변환기'로 시작하는 메인 창"으로 수정(양 언어)
- [ ] 전체 스위트 → 커밋 `Track F: 버전 표기 --version·GUI 제목 (F-1c)`

### Task 2: 문서유형 전역 상태 제거 (F-3a)

**Files:** Modify `anyway_to_hwpx_com.py` — `_ALLOW_ROMAN_LEVEL`(:195~202), `detect_and_parse`, `convert_file`(두 호출부), `main`(global 제거) / Test: `tests/test_roman_level_option.py`(전역 패치 테스트를 공개 경로 테스트로 교체 — 의도적 변경)

**Interfaces:** Produces `detect_and_parse(file_path, kordoc_home=None, pdf_mode='layout', asset_dir=None, doc_type='plan')`, `convert_file(..., pdf_mode='layout', doc_type='plan', official=False)`; `_ALLOW_ROMAN_LEVEL`은 `ContextVar[bool]`(default True)

- [ ] RED — 테스트(`RomanLevelParseWiringTests` 교체)

```python
class RomanLevelParseWiringTests(unittest.TestCase):
    def _list_depths(self, doc_type=None):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "s.md"
            source.write_text("1. 목적\n가. 세부", encoding="utf-8")
            kwargs = {} if doc_type is None else {"doc_type": doc_type}
            blocks = converter.detect_and_parse(source, **kwargs)
        return [b["depth"] for b in blocks if b.get("type") == "li"]

    def test_default_plan_keeps_roman_level(self):
        self.assertEqual(self._list_depths(), [1, 2])

    def test_sihaengmun_starts_at_number_level(self):
        self.assertEqual(self._list_depths("sihaengmun"), [0, 1])

    def test_consecutive_conversions_do_not_leak(self):
        self.assertEqual(self._list_depths("sihaengmun"), [0, 1])
        self.assertEqual(self._list_depths("plan"), [1, 2])
        self.assertTrue(converter._ALLOW_ROMAN_LEVEL.get())

    def test_unknown_doc_type_is_rejected(self):
        with self.assertRaises(ValueError):
            self._list_depths("memo")

    def test_monolith_has_no_global_statement(self):
        tree = ast.parse(Path(converter.__file__).read_text(encoding="utf-8"))
        self.assertEqual([n for n in ast.walk(tree) if isinstance(n, ast.Global)], [])
```

- [ ] GREEN

```python
import contextvars
# 항목체계 로마숫자 최상위 레벨 허용 여부(정본 §2-1). detect_and_parse가 변환 1건 범위로만 설정·복원한다.
_ALLOW_ROMAN_LEVEL = contextvars.ContextVar('allow_roman_level', default=True)
_DOC_TYPES = ('plan', 'sihaengmun')

def _detect_list_item(line):
    return detect_official_list_item(line, _clean_inline, allow_roman=_ALLOW_ROMAN_LEVEL.get())

def detect_and_parse(file_path, kordoc_home=None, pdf_mode='layout', asset_dir=None, doc_type='plan'):
    if doc_type not in _DOC_TYPES:
        raise ValueError(f'지원하지 않는 문서 유형: {doc_type} (지원: {", ".join(_DOC_TYPES)})')
    token = _ALLOW_ROMAN_LEVEL.set(doc_type != 'sihaengmun')
    try:
        return _parse_by_extension(file_path, kordoc_home=kordoc_home, pdf_mode=pdf_mode, asset_dir=asset_dir)
    finally:
        _ALLOW_ROMAN_LEVEL.reset(token)
```

기존 `detect_and_parse` 본문은 `_parse_by_extension`으로 이름만 옮김. `convert_file`은 `doc_type`을 두 `detect_and_parse` 호출에 전달, `main`은 `global` 2줄 삭제 후 `doc_type=args.doc_type` 전달.

- [ ] 전체 스위트 → 커밋 `Track F: 문서유형을 변환 범위 ContextVar로 — 전역 누수 제거 (F-3a)`

### Task 3: 공문 정규화 분리 `--official` (F-3b)

**Files:** Modify `anyway_to_hwpx_com.py` — `convert_file.convert_loaded` 정규화 블록, `main` / Test: `tests/test_conversion_notes.py`(클래스 추가)

- [ ] 특성화 테스트(현행 고정, 통과해야 정상): `--insert-end-mark` 경로의 build_doc 입력 blocks — **코드 변경 전 먼저 실행**, 실패하면 기대값을 실제 출력에 맞춰 고침(코드를 기대값에 맞추지 않음)

```python
def _captured_blocks(self, **kwargs):
    captured = []
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "s.md"
        source.write_text("2026.3.22 행사\n\n강사료 400,000원", encoding="utf-8")
        with (
            patch.object(converter, "build_doc", side_effect=lambda _hwp, blocks: captured.append(blocks)),
            patch.object(converter.time, "sleep", return_value=None),
        ):
            result = converter.convert_file(_FakeHwp(), source, Path(tmp) / "s.hwpx", **kwargs)
    return captured[0], result["notes"]

def test_insert_end_mark_keeps_current_normalization_and_end_mark(self):
    blocks, _ = self._captured_blocks(insert_end_mark=True)
    self.assertEqual(blocks, [
        {"type": "p", "text": "2026. 3. 22. 행사"},
        {"type": "p", "text": "강사료 금400,000원(금사십만원)  끝."},
    ])
```

- [ ] RED

```python
def test_official_normalizes_without_end_mark(self):
    blocks, _ = self._captured_blocks(official=True)
    self.assertEqual(blocks, [
        {"type": "p", "text": "2026. 3. 22. 행사"},
        {"type": "p", "text": "강사료 금400,000원(금사십만원)"},
    ])

def test_default_leaves_text_untouched(self):
    blocks, _ = self._captured_blocks()
    self.assertEqual(blocks, [{"type": "p", "text": "2026.3.22 행사"}, {"type": "p", "text": "강사료 400,000원"}])

def test_cli_official_flag_reaches_convert_file(self):
    ...  # main([src, '-o', tmp, '--official']) → convert_file 호출 kwargs official=True (patch)
```

- [ ] GREEN

```python
        if not rendered_layout and (official or insert_end_mark):
            blocks = normalize_official_dates(blocks)
            blocks = normalize_official_amounts(blocks)
            notes.extend(lint_official_style(blocks))
            notes.extend(lint_money_notation(blocks))
            if insert_end_mark:
                blocks = append_end_mark_blocks(blocks)
```

`main`: `--official`(help: 공문 표기 정규화(날짜·금액)와 표기 점검 — "끝" 없이. --insert-end-mark는 이를 포함) → `official=args.official`

- [ ] 전체 스위트 → 커밋 `Track F: 공문 정규화를 --official로 분리, --insert-end-mark 현행 유지 (F-3b)`

### Task 4: 시간 표기 린트 (F-3d, 경고만)

**Files:** Modify `anyway_to_hwpx_com.py`(린트 절, 정규화 블록) / Test: `tests/test_official_style_lint.py`(클래스 추가)

**Interfaces:** Produces `lint_official_time(blocks) -> list[str]`(0~1건)

**선결 결정(사용자):** 표기 린트 등급 — 기존 3종('및'·순화·천원)이 `[확인 필요]`라 웨이브 1 GUI가 해당 표현만 있어도 "변환 완료(확인 필요)"를 띄움(실측: `samples/sample_complex.md` 2건). 결정에 따라 표기 린트 접두어·GUI 집계 대상 확정 후 이 Task 진행

- [ ] RED

```python
class OfficialTimeLintTests(unittest.TestCase):
    def _lint(self, text, table=False):
        block = {"type": "table", "header": ["시간"], "rows": [[text]]} if table else {"type": "p", "text": text}
        return converter.lint_official_time([block])

    def test_pm_hour_minute_suggests_24h(self):
        notes = self._lint("오후 3시 20분 개회")
        self.assertEqual(len(notes), 1)
        self.assertIn("'오후 3시 20분' → '15:20'", notes[0])

    def test_am_hour_suggests_colon_form(self):
        self.assertIn("'오전 9시' → '9:00'", self._lint("오전 9시 집결")[0])

    def test_hour_minute_without_meridiem(self):
        self.assertIn("'14시 30분' → '14:30'", self._lint("14시 30분 종료")[0])

    def test_table_cells_are_scanned(self):
        self.assertEqual(len(self._lint("오후 2시", table=True)), 1)

    def test_duration_and_colon_form_are_not_flagged(self):
        self.assertEqual(self._lint("2시간 교육, 15:20 개회"), [])

    def test_multiple_hits_are_summarized_in_one_note(self):
        notes = self._lint("오전 9시 집결, 오후 3시 해산")
        self.assertEqual(len(notes), 1)
        self.assertIn("2건", notes[0])
```

- [ ] GREEN

```python
_TIME_EXPR_PATTERN = re.compile(r'(?:(오전|오후)\s*)?(?<!\d)(\d{1,2})\s*시(?!간)(?:\s*(\d{1,2})\s*분)?')

def _suggest_24h(match):
    meridiem, hour, minute = match.group(1), int(match.group(2)), int(match.group(3) or 0)
    if meridiem == '오후' and hour < 12:
        hour += 12
    elif meridiem == '오전' and hour == 12:
        hour = 0
    return f'{hour}:{minute:02d}'

def lint_official_time(blocks):
    """정본 §1-2 시간 표기(24시각제·쌍점) — '오후 3시 20분' 등 경고 1건으로 요약(비강제)."""
    texts = _lint_texts(blocks, include_tables=True)
    hits = [m for text in texts for m in _TIME_EXPR_PATTERN.finditer(text) if 0 <= int(m.group(2)) <= 24]
    if not hits:
        return []
    first = hits[0]
    return [f"[확인 필요] 시간 표기 {len(hits)}건: '{first.group(0).strip()}' → '{_suggest_24h(first)}' 등 — 24시각제·쌍점 표기 권장 (정본 §1-2)"]
```

(`_lint_texts`는 `lint_money_notation`의 텍스트 수집을 추출한 공용 함수 — 두 린트가 공유. 정규화 블록에 `notes.extend(lint_official_time(blocks))` 추가)

- [ ] 전체 스위트 → 커밋 `Track F: 시간 표기 린트 — 24시각제·쌍점 권장 경고 (F-3d)`

### Task 5: GUI 문서유형·정규화 선택 (F-3c)

**Files:** Modify `anyway_to_hwpx_gui.py`(변수·start_conversion·_convert_worker·_set_busy), `gui_layout.py`(옵션 행 추가), `gui_conversion_worker.py`(`ConversionSnapshot` 필드·`convert_file` 전달) / Test: `tests/test_gui_drop_wiring.py`(스냅샷 인자 — 의도적 변경)

- [ ] RED — 스냅샷 테스트 기대값을 `(tuple(["source.pdf"]), "output", False, True, "editable", True, "sihaengmun")`로 바꾸고 fake app에 `official=Value(True)`, `doc_type=Value("sihaengmun")` 추가. worker 테스트: `convert_file` patch의 `call_args.kwargs`에 `official`·`doc_type` 전달 확인
- [ ] GREEN — `self.official = tk.BooleanVar(value=False)`, `self.doc_type = tk.StringVar(value="plan")`; `ConversionSnapshot`에 `official: bool = False`, `doc_type: str = "plan"`; `run_conversion`이 `official=snapshot.official, doc_type=snapshot.doc_type` 전달; `gui_layout.build_ui`에 `doc_frame`(row=3): 라벨 "문서 유형" + 라디오 "계획·보고(Ⅰ.부터)"/"시행문(1.부터)" + 체크 "공문 표기 정규화(날짜·금액·표기 점검)"; PDF 행 row=4로 이동; `_set_busy`에 신규 컨트롤 3개 포함
- [ ] "끝" 체크박스 문구에 "(정규화 포함)" 추가 — 끝을 켜면 정규화가 함께 적용됨을 표시(정규화 체크 해제가 무효인 혼동 방지)
- [ ] GUI 상태 하네스 7개 exit 0 + 최소 크기(700×560) 캡처로 새 행 잘림 여부 확인 → 커밋 `Track F: GUI 문서유형·공문 표기 정규화 선택 (F-3c)`

### Task 6: 변환 직후 자가검증 (F-2c)

**Files:** Modify `anyway_to_hwpx_com.py`(`self_check_hwpx`, `convert_loaded` 두 반환부) / Test: `tests/test_conversion_notes.py`(클래스 추가)

**Interfaces:** Produces `self_check_hwpx(hwpx_path) -> list[str]` (`[확인 필요] 산출물 자가검증: …`)

- [ ] 사전 확인은 Task 7의 레이아웃 모드 PDF 실변환(무후처리 한글 저장본)으로 대체 — 사용자 Vault 파일은 열지 않음. 자가검증 note가 나오면 루트 선언 검사를 후처리 경로에만 적용
- [ ] RED — 픽스처 4종(정상·mimetype 순서 위반·XML 파손·rowCnt 누락)

```python
def _package(path, *, mimetype_first=True, broken_section=False, drop_rowcnt=False):
    ns = " ".join(f'xmlns:{p}="{u}"' for p, u in HWPML_ROOT_NAMESPACES.items())
    tbl = '<hp:tbl colCnt="1"/>' if drop_rowcnt else '<hp:tbl rowCnt="1" colCnt="1"/>'
    section = f'<?xml version="1.0"?><hs:sec {ns}><hp:p>{tbl}</hp:p></hs:sec>'
    if broken_section:
        section = section.replace("</hs:sec>", "")
    header = f'<?xml version="1.0"?><hh:head {ns}/>'
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        entries = [("mimetype", "application/hwp+zip", zipfile.ZIP_STORED),
                   ("Contents/header.xml", header, zipfile.ZIP_DEFLATED),
                   ("Contents/section0.xml", section, zipfile.ZIP_DEFLATED)]
        if not mimetype_first:
            entries.append(entries.pop(0))
        for name, text, method in entries:
            zf.writestr(zipfile.ZipInfo(name), text, compress_type=method)
```

정상 → `[]`, 나머지 3종 → 각 1건 이상 `[확인 필요] 산출물 자가검증`, ZIP 아님 → 1건

- [ ] GREEN — 표준 라이브러리 구현(ZIP 열기, 첫 엔트리 `mimetype`·STORED, `*.xml`·`*.hpf` 파싱, header·section 루트 시작 태그에 `HWPML_ROOT_NAMESPACES` 15종 선언, section의 모든 `hp:tbl`에 `rowCnt`·`colCnt`), `convert_loaded`에서 `notes.extend(self_check_hwpx(out))`(후처리 뒤, 사전 확인 결과에 따라 레이아웃 경로 포함 여부 결정). 진단 단계 이름은 추가하지 않음(기존 단계 계약 유지)
- [ ] 전체 스위트 → 커밋 `Track F: 변환 직후 산출물 자가검증 (F-2c)`

### Task 7: 실COM 검증·기록

- [ ] 정적: 전체 스위트, `py_compile`, AST `global` 0건, GUI 하네스 7개
- [ ] 실COM(사용자 폴더 하위 `tests/out/track-f/w2/`). 시작 전 `tasklist`에 `Hwp.exe`가 있으면 **중단하고 사용자에게 문의**(사용 중 세션과 병행 금지):
  - 레이아웃 모드 텍스트 PDF 1건 → 자가검증 note 0건(무후처리 한글 저장본의 루트 선언 확인 겸)
  - `--doc-type sihaengmun` 변환 → 목록 paraPr `hc:left`가 §8 기록값(1.→620·가.→960)과 일치
  - `--official` 변환 → 산출물 본문에 `2026. 3. 22.`·`금400,000원(금사십만원)` 존재·"끝." 부재, 시간 린트 note 1건
  - 두 산출물 모두 자가검증 note 0건·안전 게이트 PASS, 한글 재열람·PDF 1쪽 렌더 육안 확인
- [ ] 기록: `IMPROVEMENT_PLAN.md` §11-11 웨이브 2 결과표, `verification-log.md`, 구현 명세 체크박스 → 커밋 `Track F: 웨이브 2 검증 결과 기록`
- [ ] 통합: 브랜치 테스트 green 확인 후 사용자에게 병합·push 여부 확인(push는 L4)
