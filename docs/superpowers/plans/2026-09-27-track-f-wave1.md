# Track F 웨이브 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 변환 중 발생하는 모든 경고가 CLI·GUI에 같은 경로로 도달하게 하고(F-2), 공개 배포본·저장소를 정상화할 준비를 마친다(F-1).

**Architecture:** 기존 note 수집 경로(`_add_conversion_note` → `result['notes']`)를 유일한 경고 채널로 삼는다. 후처리 모듈(`table_hwpx_postprocess.py`)은 순환 import를 피하려고 note 목록을 반환하고, 모놀리스 래퍼가 수집 경로에 합류시킨다. GUI worker는 note 접두어(`[경고]`·`[확인 필요]`)로 파일별 경고를 집계해 완료 메시지에 싣는다.

**Tech Stack:** Python 3.14 표준 라이브러리, unittest, Tkinter, pywin32(HWP COM, 실물 검증 단계만), PyInstaller 6.20.0(exe 판독만)

**Spec:** `IMPROVEMENT_PLAN.md` §11 (특히 11-4 하류 호환 계약, 11-5 F-1·F-2)

## Global Constraints

- CLI 위치 인자 `files`, `-o/--output-dir`, `--insert-end-mark`의 현행 의미와 종료코드 0·1·2 유지
- `main`·`convert_file`의 기존 인자 순서·기본값 유지, 신규 인자는 키워드·기본값으로만 추가
- 모놀리스 외부 참조 심볼 64개의 `anyway_to_hwpx_com` import 경로 유지
- 신규 의존성 추가 금지(표준 라이브러리만)
- note 접두어 체계: `[경고]`(서식·구조 후처리 실패 등 결과 품질 저하) / `[확인 필요]`(사용자가 원고·결과를 직접 확인해야 함) / `[참고]`(정상 동작의 정보)·`[보완]`(자동 복구)
- 한글 경로를 Bash 명령에 쓰지 않는다 — 검증 스크립트는 저장소 상대 경로 `tests/out/track-f/`(gitignore 대상)에 두고 `python tests/out/track-f/<script>.py`로 실행
- push·릴리스 발행은 Task 9의 최종 확인 후에만 실행
- 커밋 메시지는 `.git/TRACKF_MSG`에 UTF-8로 쓴 뒤 `git commit -F .git/TRACKF_MSG`, 끝에 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`

---

### Task 1: 표 후처리 경고를 note 목록으로 반환

**Files:**
- Modify: `table_hwpx_postprocess.py:6` (`import sys` 제거 — 3곳 print 전용이었음), `:221-319`
- Test: `tests/test_table_merge_postprocess.py` (클래스 추가)

**Interfaces:**
- Produces: `table_hwpx_postprocess.apply_table_layout_profiles(hwpx_path, table_layouts) -> list[str]`, `apply_table_width_profiles(...) -> list[str]` — 경고 note 목록(없으면 `[]`)

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_table_merge_postprocess.py` 끝(`if __name__` 앞)에 추가

```python
class TablePostprocessNotesTests(unittest.TestCase):
    def test_out_of_range_merge_is_returned_as_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.hwpx"
            write_hwpx(path, make_table_with_rows(rows=2, cols=3))
            layout = {"header": ["a", "b", "c"], "rows": [["1", "2", "3"]], "merged_cells": [[0, 0, 1, 5]]}
            notes = tpp.apply_table_layout_profiles(path, [layout])
        self.assertEqual(notes, ["[경고] 격자 범위를 벗어난 병합 1건 무시"])

    def test_unreadable_package_is_returned_as_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.hwpx"
            path.write_bytes(b"not a zip")
            notes = tpp.apply_table_layout_profiles(path, [{"header": ["a"], "rows": [["1"]]}])
        self.assertEqual(len(notes), 1)
        self.assertTrue(notes[0].startswith("[경고] 표 후처리 준비 실패"))

    def test_clean_table_returns_no_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.hwpx"
            write_hwpx(path, make_table_with_rows(rows=2, cols=3))
            layout = {"header": ["a", "b", "c"], "rows": [["1", "2", "3"]], "merged_cells": []}
            notes = tpp.apply_table_layout_profiles(path, [layout])
        self.assertEqual(notes, [])
```

- [ ] **Step 2: 실패 확인** — `python -m unittest tests.test_table_merge_postprocess.TablePostprocessNotesTests -v` → 3건 FAIL(`None != [...]`)

- [ ] **Step 3: 최소 구현** — `table_hwpx_postprocess.py`

```python
def apply_table_layout_profiles(hwpx_path, table_layouts: Sequence[TableLayout | TableBlock]) -> list[str]:
    return apply_table_width_profiles(hwpx_path, table_layouts)


def apply_table_width_profiles(hwpx_path, table_layouts: Sequence[TableLayout | TableBlock]) -> list[str]:
    """표 폭·테두리·병합 후처리. 반환: 사용자에게 전달할 경고 note 목록(없으면 빈 목록)."""
    notes: list[str] = []
    if not table_layouts or not os.path.exists(hwpx_path):
        return notes
    ...
    except (KeyError, OSError, zipfile.BadZipFile) as exc:
        notes.append(f"[경고] 표 후처리 준비 실패: {exc}")
        return notes
    ...
            if dropped_spans:
                notes.append(f"[경고] 격자 범위를 벗어난 병합 {len(dropped_spans)}건 무시")
    ...
    except (ET.ParseError, OSError, ValueError, zipfile.BadZipFile) as exc:
        notes.append(f"[경고] 표 후처리 실패: {exc}")
    return notes
```

`import sys`(6행) 삭제.

- [ ] **Step 4: 통과 확인** — 같은 명령 → 3건 PASS, 이어서 `python -m unittest tests.test_table_merge_postprocess -v` 전체 PASS

- [ ] **Step 5: 커밋** — `git add table_hwpx_postprocess.py tests/test_table_merge_postprocess.py` / 메시지 `Track F: 표 후처리 경고를 note 목록으로 반환 (F-2a)`

---

### Task 2: 모놀리스 경고 print → note 수집, 수집 시점을 후처리 이후로

**Files:**
- Modify: `anyway_to_hwpx_com.py` — `_add_conversion_note`(859-861), `apply_list_hanging_indents`(1951-1952), `fix_body_text_prid`(2030-2031), `apply_official_line_spacing`(2080-2081), `apply_official_paragraph_spacing`(2216-2217·2223-2224), `apply_official_page_margins`(2249-2250), `apply_table_layout_profiles`(2271-2272), `convert_file.convert_loaded`(2882-2894)
- Create: `tests/test_conversion_notes.py`

**Interfaces:**
- Consumes: Task 1의 `list[str]` 반환
- Produces: `convert_file(...)['notes']`에 파싱·린트·빌드·후처리 note가 이 순서로 모두 포함 / `_add_conversion_note`는 수집만 하고 출력하지 않음(CLI 출력은 `main`이 파일별 1회)

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_conversion_notes.py` 신설

```python
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import anyway_to_hwpx_com as converter


class _FakeDocument:
    def Close(self, isDirty=False):
        return None


class _FakeDocuments:
    def __init__(self):
        self.docs = []

    @property
    def Count(self):
        return len(self.docs)

    def Add(self, isTab=False):
        self.docs.append(_FakeDocument())

    def Item(self, index):
        return self.docs[index]


class _FakeHwp:
    """SaveAs가 ZIP이 아닌 바이트를 쓰므로 모든 XML 후처리가 실패한다."""

    def __init__(self):
        self.XHwpDocuments = _FakeDocuments()

    def SaveAs(self, output_path, format_name, option):
        Path(output_path).write_bytes(b"saved")

    def Quit(self):
        return None


BLOCKS = [{"type": "p", "text": "본문"}, {"type": "table", "header": ["구분"], "rows": [["값"]]}]


class PostprocessNoteRoutingTests(unittest.TestCase):
    def setUp(self):
        converter.pop_conversion_notes()

    def test_every_postprocess_failure_surfaces_in_result_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "sample.md"
            source.write_text("# 제목", encoding="utf-8")
            with (
                patch.object(converter, "detect_and_parse", return_value=list(BLOCKS)),
                patch.object(converter, "build_doc", return_value=None),
                patch.object(converter.time, "sleep", return_value=None),
            ):
                result = converter.convert_file(_FakeHwp(), source, Path(tmp) / "sample.hwpx")

        notes = result["notes"]
        for label in ("페이지 여백", "표 후처리", "목록 내어쓰기", "본문 단락 paraPr", "줄 간격", "단락 간격"):
            self.assertTrue(
                any(note.startswith("[경고]") and label in note for note in notes),
                f"{label} 경고 누락: {notes}",
            )

    def test_main_prints_each_note_exactly_once(self):
        def fake_parse(*_args, **_kwargs):
            converter._add_conversion_note("[참고] 테스트 노트")
            return [{"type": "p", "text": "본문"}]

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "sample.md"
            source.write_text("# 제목", encoding="utf-8")
            stdout, stderr = io.StringIO(), io.StringIO()
            with (
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
                patch.object(converter, "create_hwp_object", return_value=_FakeHwp()),
                patch.object(converter, "detect_and_parse", side_effect=fake_parse),
                patch.object(converter, "build_doc", return_value=None),
                patch.object(converter.time, "sleep", return_value=None),
            ):
                exit_code = converter.main([str(source), "-o", tmp])

        self.assertEqual(exit_code, 0)
        self.assertEqual((stdout.getvalue() + stderr.getvalue()).count("[참고] 테스트 노트"), 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패 확인** — `python -m unittest tests.test_conversion_notes -v` → 2건 FAIL(경고 누락 / 노트 2회 출력)

- [ ] **Step 3: 최소 구현** — `anyway_to_hwpx_com.py`

```python
def _add_conversion_note(message):
    _conversion_notes.append(message)
```

경고 print 6곳 치환:

```python
        _add_conversion_note(f'[경고] 목록 내어쓰기 후처리 실패: {e}')      # apply_list_hanging_indents
        _add_conversion_note(f'[경고] 본문 단락 paraPr 보정 실패: {e}')     # fix_body_text_prid
        _add_conversion_note(f'[경고] 줄 간격 후처리 실패: {e}')            # apply_official_line_spacing
            _add_conversion_note(f'[참고] 제목 단락 간격: 공유 paraPr {cloned}건 분리 적용 (§7-3)')
        _add_conversion_note(f'[경고] 단락 간격 후처리 실패: {e}')          # apply_official_paragraph_spacing
        _add_conversion_note(f'[경고] 페이지 여백 후처리 실패: {e}')        # apply_official_page_margins
```

래퍼:

```python
def apply_table_layout_profiles(hwpx_path, table_layouts):
    for note in _apply_table_layout_profiles_new(hwpx_path, table_layouts) or ():
        _add_conversion_note(note)
```

`convert_loaded`의 두 반환 직전에 빌드·후처리 note 합류:

```python
        if rendered_layout:
            notes.extend(pop_conversion_notes())
            return {'notes': notes}
        ...
        apply_official_paragraph_spacing(out)
        notes.extend(pop_conversion_notes())
        if diagnose_stage:
            diagnose_stage('finalize')
        return {'notes': notes}
```

- [ ] **Step 4: 통과 확인** — `python -m unittest tests.test_conversion_notes -v` PASS → `python -m unittest discover -s tests` 전체 PASS(기존 243 + 신규, skip 1)

- [ ] **Step 5: 커밋** — `git add anyway_to_hwpx_com.py tests/test_conversion_notes.py` / 메시지 `Track F: 후처리 경고를 note 수집 경로로 통합, CLI 중복 출력 제거 (F-2a)`

---

### Task 3: `TableColWidth` 미지원은 변환당 1회 `[참고]`

**Files:**
- Modify: `anyway_to_hwpx_com.py` — `insert_table`(2280-2348), `build_doc`(2415-2491)
- Test: `tests/test_conversion_notes.py` (클래스 추가)

**Interfaces:**
- Produces: `insert_table(..., merged_cells=None, try_col_width=True) -> bool` — `TableColWidth` 액션 사용 가능 여부(미시도·정상 시 `True`, 액션이 `None`이면 `False`)

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_conversion_notes.py`에 추가

```python
class _Action:
    def CreateSet(self):
        return self

    def GetDefault(self, _pset):
        return None

    def SetItem(self, _name, _value):
        return None

    def Execute(self, _pset):
        return True


class _HAction:
    def GetDefault(self, _name, _hset):
        return None

    def Execute(self, _name, _hset):
        return True

    def Run(self, _name):
        return True


class _InsertText:
    HSet = object()
    Text = ""


class _ParameterSets:
    HInsertText = _InsertText()


class _TableHwp:
    def __init__(self, col_width_error=None):
        self.col_width_requests = 0
        self.col_width_error = col_width_error
        self.HAction = _HAction()
        self.HParameterSet = _ParameterSets()

    def CreateAction(self, name):
        if name == "TableColWidth":
            self.col_width_requests += 1
            if self.col_width_error is not None:
                raise self.col_width_error
            return None
        return _Action()


TWO_TABLES = [
    {"type": "table", "header": ["구분", "내용"], "rows": [["가", "나"]]},
    {"type": "table", "header": ["항목", "비고"], "rows": [["다", "라"]]},
]


class TableColWidthNoteTests(unittest.TestCase):
    def setUp(self):
        converter.pop_conversion_notes()

    def test_unavailable_action_is_probed_once_and_reported_as_info(self):
        hwp = _TableHwp()
        converter.build_doc(hwp, TWO_TABLES)
        notes = converter.pop_conversion_notes()

        self.assertEqual(hwp.col_width_requests, 1)
        self.assertEqual([n for n in notes if "TableColWidth" in n], [
            "[참고] 표 열 너비: 이 한글 버전은 TableColWidth 미지원 — XML 후처리로 적용",
        ])
        self.assertFalse(any(n.startswith("[경고] 열 너비") for n in notes))

    def test_unexpected_action_error_is_reported_as_warning(self):
        hwp = _TableHwp(col_width_error=RuntimeError("COM 오류"))
        converter.build_doc(hwp, TWO_TABLES[:1])
        notes = converter.pop_conversion_notes()

        self.assertIn("[경고] 열 너비 조정 실패: COM 오류", notes)
```

- [ ] **Step 2: 실패 확인** — `python -m unittest tests.test_conversion_notes.TableColWidthNoteTests -v` → FAIL(요청 2회·note 없음)

- [ ] **Step 3: 최소 구현** — `insert_table` 열 폭 블록 교체(미사용 변수 `width_adjust_failed` 소멸)

```python
def insert_table(hwp, header, rows, table_role=None, column_widths=None, table_source=None,
                 worksheet_title=None, merged_cells=None, try_col_width=True):
    """표 삽입. 반환: TableColWidth 액션 사용 가능 여부(액션이 None이면 False).

    열 너비는 XML 후처리(apply_table_layout_profiles)가 최종 적용하므로 COM 조정은 보조다.
    """
    ...
    _require_hwp_success(act.Execute(pset), 'TableCreate')
    col_width_available = True
    moved_right = 0
    if try_col_width:
        try:
            for ci, w in enumerate(col_widths):
                sel_act = hwp.CreateAction('TableColWidth')
                if sel_act is None:
                    col_width_available = False
                    break
                sel_pset = sel_act.CreateSet()
                sel_act.GetDefault(sel_pset)
                sel_pset.SetItem('Width', w)
                sel_act.Execute(sel_pset)
                if ci < num_cols - 1:
                    hwp.HAction.Run('TableRightCell')
                    moved_right += 1
        except Exception as e:
            _add_conversion_note(f'[경고] 열 너비 조정 실패: {e}')
        finally:
            for _ in range(moved_right):
                hwp.HAction.Run('TableLeftCell')
    ...  # 셀 채우기·MoveDocEnd·break_para 무변경
    return col_width_available
```

`build_doc`:

```python
def build_doc(hwp, blocks):
    first_depth1_li_seen = False
    col_width_supported = True
    ...
        elif t == 'table':
            ...
            available = insert_table(
                hwp,
                ...
                merged_cells=blk.get('merged_cells') or blk.get('merges'),
                try_col_width=col_width_supported,
            )
            if col_width_supported and not available:
                col_width_supported = False
                _add_conversion_note('[참고] 표 열 너비: 이 한글 버전은 TableColWidth 미지원 — XML 후처리로 적용')
            _blank_line(hwp)
```

- [ ] **Step 4: 통과 확인** — 대상 테스트 PASS → 전체 스위트 PASS(`tests/test_pdf_hwp_image_writer.py`의 `insert_table` TableCreate 실패 테스트 포함)

- [ ] **Step 5: 커밋** — 메시지 `Track F: TableColWidth 미지원은 변환당 1회 [참고]로 보고 (F-2d)`

---

### Task 4: Markdown 이미지 `!alt` 잔류 결함 수정 + 이미지·링크 건수 note

**Files:**
- Modify: `anyway_to_hwpx_com.py` — `_clean_inline`(127-137), `parse_markdown` 반환 직전(369)
- Test: `tests/test_conversion_notes.py` (클래스 추가)

**Interfaces:**
- Produces: `_markdown_media_counts(text) -> tuple[int, int]` (코드 블록 밖 이미지·링크 수)

- [ ] **Step 1: 실패 테스트 작성**

```python
class MarkdownMediaTests(unittest.TestCase):
    def setUp(self):
        converter.pop_conversion_notes()

    def test_image_with_alt_text_leaves_no_residue(self):
        blocks = converter.parse_markdown("![현황 그래프](chart.png)\n\n본문")
        self.assertEqual(blocks, [{"type": "p", "text": "본문"}])

    def test_inline_image_and_link_cleanup(self):
        self.assertEqual(converter._clean_inline("앞 ![그림](a.png)뒤 [안내](https://x.kr)"), "앞 뒤 안내")

    def test_media_counts_become_notes_excluding_code_blocks(self):
        converter.parse_markdown("![a](a.png) [링크](https://x.kr)\n```\n![b](b.png)\n```\n본문")
        notes = converter.pop_conversion_notes()
        self.assertEqual(notes, [
            "[확인 필요] Markdown 이미지 1개 미삽입(이미지 삽입 미지원) — 필요 시 한글에서 직접 삽입",
            "[참고] Markdown 링크 1개는 표시 텍스트만 유지(URL 제외)",
        ])

    def test_plain_markdown_adds_no_media_notes(self):
        converter.parse_markdown("# 제목\n\n본문")
        self.assertEqual(converter.pop_conversion_notes(), [])
```

- [ ] **Step 2: 실패 확인** — `python -m unittest tests.test_conversion_notes.MarkdownMediaTests -v` → FAIL(`!현황 그래프` 잔류, note 없음)

- [ ] **Step 3: 최소 구현**

```python
_MD_IMAGE_PATTERN = re.compile(r'!\[[^\]]*\]\([^\)]+\)')
_MD_LINK_PATTERN = re.compile(r'\[([^\]]+)\]\([^\)]+\)')


def _clean_inline(text):
    text = _MD_IMAGE_PATTERN.sub('', text)  # 링크보다 먼저 — 순서가 바뀌면 '!alt'가 남음
    text = _MD_LINK_PATTERN.sub(r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    ...  # 이하 무변경


def _markdown_media_counts(text):
    """코드 블록 밖 Markdown 이미지·링크 수 (parse_markdown과 같은 ``` 경계 규칙)."""
    images = links = 0
    in_code = False
    for line in text.splitlines():
        if line.strip().startswith('```'):
            in_code = not in_code
            continue
        if in_code:
            continue
        images += len(_MD_IMAGE_PATTERN.findall(line))
        links += len(_MD_LINK_PATTERN.findall(_MD_IMAGE_PATTERN.sub('', line)))
    return images, links
```

`parse_markdown`의 `return blocks` 직전:

```python
    images, links = _markdown_media_counts(text)
    if images:
        _add_conversion_note(f'[확인 필요] Markdown 이미지 {images}개 미삽입(이미지 삽입 미지원) — 필요 시 한글에서 직접 삽입')
    if links:
        _add_conversion_note(f'[참고] Markdown 링크 {links}개는 표시 텍스트만 유지(URL 제외)')
    return blocks
```

(`"앞 ![그림](a.png)뒤"` → 이미지 제거 후 `"앞 뒤"` — 테스트 기대값이 공백 1개가 되도록 입력에서 이미지 뒤 공백을 두지 않음.)

- [ ] **Step 4: 통과 확인** — 대상 테스트 PASS → 전체 스위트 PASS

- [ ] **Step 5: 커밋** — 메시지 `Track F: Markdown 이미지 !alt 잔류 수정 + 이미지·링크 건수 note (F-2e)`

---

### Task 5: Java 11 미만 안내 한국어화 + README 요건 보강 (E-6 흡수)

**Files:**
- Modify: `anyway_to_hwpx_com.py:1640-1649`, `README.ko.md`·`README.md`(요구 사항 목록)
- Test: `tests/test_pdf_mode_wiring.py:254-268` (의도적 계약 변경 — 영문 → 한국어)

- [ ] **Step 1: 테스트 기대값 변경(RED)** — `test_editable_pdf_reports_java_fallback_note_when_odl_is_unavailable`의 단언을 교체

```python
        self.assertEqual(len(notes), 1)
        self.assertTrue(notes[0].startswith("[참고] PDF 편집 모드"))
        self.assertIn("Java 8", notes[0])
        self.assertIn("Java 11 이상", notes[0])
```

추가 테스트(Java 미확인 분기):

```python
    def test_editable_pdf_reports_generic_fallback_note_without_java_version(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.pdf"
            source.write_bytes(b"%PDF")
            capabilities = SimpleNamespace(pdf_enabled=True, odl_enabled=False, java_major=None)
            with patch.object(converter, "detect_capabilities", return_value=capabilities), patch.object(
                converter, "parse_pdf", return_value=[{"type": "p", "text": "fallback"}]
            ):
                converter.detect_and_parse(source, pdf_mode="editable")
                notes = converter.pop_conversion_notes()

        self.assertEqual(len(notes), 1)
        self.assertTrue(notes[0].startswith("[참고] PDF 편집 모드"))
        self.assertIn("Java 11 이상", notes[0])
```

- [ ] **Step 2: 실패 확인** — `python -m unittest tests.test_pdf_mode_wiring -v` → 2건 FAIL

- [ ] **Step 3: 구현**

```python
        if pdf_mode == PdfMode.EDITABLE.value and not capabilities.odl_enabled:
            if capabilities.java_major is not None and capabilities.java_major < 11:
                reason = f'Java {capabilities.java_major}(11 미만)이라 opendataloader-pdf를 쓸 수 없어'
            else:
                reason = 'opendataloader-pdf를 쓸 수 없어'
            _add_conversion_note(
                f'[참고] PDF 편집 모드: {reason} pdfplumber·PyMuPDF·pypdf 대체 추출 사용 — '
                '표·읽기 순서 품질을 높이려면 Java 11 이상 설치 후 full 스택 사용'
            )
```

README 요구 사항 목록에 1줄 추가 — `README.ko.md`: `- PDF 편집 모드 고품질 추출(선택): Java 11 이상 — 미충족 시 대체 추출로 자동 전환되고 변환 로그에 안내 표시` / `README.md`: `- Higher-quality editable PDF extraction (optional): Java 11+ — otherwise the converter falls back automatically and notes it in the conversion log`

- [ ] **Step 4: 통과 확인** — 대상 테스트 PASS → 전체 스위트 PASS

- [ ] **Step 5: 커밋** — 메시지 `Track F: PDF 편집 모드 Java 안내 한국어화·조치 안내 (F-2f, E-6)`

---

### Task 6: GUI — 경고 note 파일을 결과 상태에 반영

**Files:**
- Modify: `gui_conversion_worker.py`, `anyway_to_hwpx_gui.py:241-248`, `gui_input_status.py:38-64`
- Test: `tests/test_gui_drop_wiring.py:158`(완료 메시지 4요소로 의도적 변경), `tests/test_gui_input_status.py`(클래스 추가)

**Interfaces:**
- Produces: `gui_conversion_worker.note_log_tag(note: str) -> str` (`"err"`·`"warn"`·`"muted"`) / 완료 메시지 `("done", completed: int, failures: list[Failure], warned: list[str])` / `gui_input_status.finish_conversion(app, completed, failures, warned=())`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_gui_drop_wiring.py:158` 기대값을 `("done", 1, [], [])`로 변경.

`tests/test_gui_input_status.py`에 추가:

```python
from unittest.mock import patch

import gui_input_status
from gui_conversion_worker import note_log_tag


class _Progress:
    def configure(self, **kwargs):
        self.config = kwargs


class _FinishApp(_App):
    def __init__(self) -> None:
        super().__init__()
        self.progress = _Progress()
        self.output_dir = _Value()
        self.busy_states: list[bool] = []

    def _set_busy(self, busy: bool) -> None:
        self.busy_states.append(busy)


class FinishConversionTests(unittest.TestCase):
    def test_note_tags_follow_prefix_severity(self) -> None:
        self.assertEqual(note_log_tag("[확인 필요] Markdown 이미지 1개 미삽입"), "err")
        self.assertEqual(note_log_tag("[경고] 줄 간격 후처리 실패: x"), "warn")
        self.assertEqual(note_log_tag("[참고] 표 열 너비"), "muted")

    def test_warned_files_produce_warning_summary_instead_of_plain_success(self) -> None:
        app = _FinishApp()
        with patch.object(gui_input_status.messagebox, "askyesno", return_value=False) as ask:
            gui_input_status.finish_conversion(app, 2, [], ["a.md"])

        self.assertIn("확인 필요 1개", app.status.value)
        self.assertEqual(ask.call_args.args[0], "변환 완료(확인 필요)")
        self.assertIn("a.md", ask.call_args.args[1])

    def test_clean_run_keeps_plain_success_dialog(self) -> None:
        app = _FinishApp()
        with patch.object(gui_input_status.messagebox, "askyesno", return_value=False) as ask:
            gui_input_status.finish_conversion(app, 2, [], [])

        self.assertEqual(app.status.value, "전체 변환 완료: 2개")
        self.assertEqual(ask.call_args.args[0], "변환 완료")
```

- [ ] **Step 2: 실패 확인** — `python -m unittest tests.test_gui_input_status tests.test_gui_drop_wiring -v` → FAIL(`note_log_tag` import 실패, done 3요소)

- [ ] **Step 3: 구현**

`gui_conversion_worker.py`:

```python
ConversionMessage: TypeAlias = (
    tuple[str, int, int, str]
    | tuple[str, str, str | None]
    | tuple[str, int, list[Failure], list[str]]
)
_WARNING_PREFIXES = ("[경고]", "[확인 필요]")


def note_log_tag(note: str) -> str:
    if note.startswith("[확인 필요]"):
        return "err"
    if note.startswith("[경고]"):
        return "warn"
    return "muted"
```

`run_conversion`: `warned: list[str] = []` 선언, note 루프 교체, 완료 메시지 확장

```python
                notes = (result or {}).get("notes", [])
                for note in notes:
                    message_sink(("log", note, note_log_tag(note)))
                if any(note.startswith(_WARNING_PREFIXES) for note in notes):
                    warned.append(src_path.name)
    ...
        message_sink(("done", completed, failures, warned))
```

`anyway_to_hwpx_gui.py`:

```python
                elif msg[0] == "done":
                    self._finish_conversion(msg[1], msg[2], msg[3])
    ...
    def _finish_conversion(self, completed, failures, warned=()):
        finish_conversion(self, completed, failures, warned)
```

`gui_input_status.py`:

```python
def _offer_output_folder(app, title: str, message: str) -> None:
    if messagebox.askyesno(title, message):
        out_dir = app.output_dir.get().strip()
        if out_dir and os.path.isdir(out_dir):
            os.startfile(out_dir)


def finish_conversion(app, completed, failures, warned=()) -> None:
    app.progress.configure(value=completed)
    app._set_busy(False)
    if failures:
        ...  # 무변경
    elif warned:
        app.status.set(f"변환 완료 {completed}개 · 확인 필요 {len(warned)}개 — 로그를 확인하세요")
        lines = [f"• {name}" for name in warned[:5]]
        if len(warned) > 5:
            lines.append(f"... 외 {len(warned) - 5}개")
        _offer_output_folder(
            app,
            "변환 완료(확인 필요)",
            f"{completed}개 파일을 변환했습니다. 다음 파일에 경고가 있습니다.\n\n"
            + "\n".join(lines)
            + "\n\n로그에서 내용을 확인하세요. 저장 폴더를 열까요?",
        )
    else:
        app.status.set(f"전체 변환 완료: {completed}개")
        _offer_output_folder(app, "변환 완료", f"{completed}개 파일을 변환했습니다.\n저장 폴더를 열까요?")
```

- [ ] **Step 4: 통과 확인** — 대상 테스트 PASS → 전체 스위트 PASS → `python tests/gui_state_harness.py --state warning --hold-seconds 0.2` exit 0

- [ ] **Step 5: 커밋** — 메시지 `Track F: GUI 경고 note를 파일별 결과 상태에 반영 (F-2b)`

---

### Task 7: 저장소·문서 정리 (F-1b 로컬분·F-1d·F-1e)

**Files:**
- Modify: 추적 해제 `dist/anyway_to_hwpx_gui.exe`(디스크 파일은 유지), `README.ko.md`·`README.md`(개발자 절 릴리스 체크리스트), `IMPROVEMENT_PLAN.md` §10-3(N14 정정)
- Local only(gitignore): `handoff.md`

- [ ] **Step 1: exe 추적 해제** — `git rm --cached dist/anyway_to_hwpx_gui.exe` → `git ls-files dist` 결과 없음, `ls dist/anyway_to_hwpx_gui.exe` 존재 확인

- [ ] **Step 2: README 릴리스 체크리스트** — 개발자 절 "GUI 실행 파일 빌드" 뒤에 추가(`README.ko.md`)

```markdown
### 릴리스 절차

1. `python -m unittest discover -s tests`·`python -m py_compile anyway_to_hwpx_com.py anyway_to_hwpx_gui.py` 통과
2. 샘플 실변환 후 `python scripts/hwpx_editor_safety_gate.py <산출물>` PASS, 한글에서 열어 여백·글꼴 육안 확인
3. 격리 빌드(위 명령) 후 실행 파일 기동 확인
4. 실행 파일 SHA-256·크기 기록 → GitHub Release에 첨부(태그는 빌드한 커밋에). 실행 파일은 저장소에 커밋하지 않음
```

`README.md`에 같은 내용 영문(`### Release checklist`).

- [ ] **Step 3: §10-3 정정** — `IMPROVEMENT_PLAN.md` §10-3 "skip 1건(bs4 미설치)의 처리 방침은 이번 회차에서 결정하지 않음" 줄 뒤에 `- **정정(2026-09-27, Track F N14)**: 현 환경 skip 1건은 COM 통합 테스트 게이트(`HWPX_RUN_COM_TESTS` 미설정)이며 bs4 4.14.3 설치 확인 — 방침 결정 불요, 종결.` 추가

- [ ] **Step 4: dist 안내 문서 점검** — `dist/` 사용 안내 txt·html에서 `layout`·`편집`·`PDF 모드`·`끝` 언급을 Grep → 현행 기능 반영 여부를 결과 보고에만 기록(파일 수정은 사용자 확인 후)

- [ ] **Step 5: 커밋** — `git add README.ko.md README.md IMPROVEMENT_PLAN.md` + 스테이징된 exe 삭제 / 메시지 `Track F: exe 추적 해제·릴리스 체크리스트·기록 정정 (F-1b·F-1d·F-1e)` (`handoff.md`는 Task 8 뒤 로컬 갱신)

---

### Task 8: 웨이브 1 실물 검증 + 결과 기록

**Files:**
- Create(gitignore): `tests/out/track-f/wave1_check.md`, `tests/out/track-f/verify_wave1.py`
- Modify: `IMPROVEMENT_PLAN.md` §11(결과 절), `verification-log.md`, `handoff.md`(로컬)

- [ ] **Step 1: 정적 검증** — `python -m unittest discover -s tests` 전체 PASS(skip 1) · `python -m py_compile anyway_to_hwpx_com.py anyway_to_hwpx_gui.py table_hwpx_postprocess.py gui_conversion_worker.py gui_input_status.py` · grep: `anyway_to_hwpx_com.py`·`table_hwpx_postprocess.py`에서 `[경고]`를 `print`로 내보내는 줄 0건

- [ ] **Step 2: 검증 원고 작성** — `tests/out/track-f/wave1_check.md`: 제목·항목(1. 가.)·표 2개·alt 있는 이미지 1개·링크 1개·금액·날짜 포함

- [ ] **Step 3: 실COM 변환** — `python anyway_to_hwpx_com.py --preflight` OK 후 `python anyway_to_hwpx_com.py tests/out/track-f/wave1_check.md -o tests/out/track-f --insert-end-mark` → 판정: `[참고] 표 열 너비` 1회, `[확인 필요] Markdown 이미지 1개` 1회, 각 note 1회 출력, 종료코드 0

- [ ] **Step 4: 구조·실물 검증** — `python scripts/hwpx_editor_safety_gate.py tests/out/track-f/wave1_check.hwpx` PASS → `verify_wave1.py`: 산출물 XML에서 `!` 잔류·alt 텍스트 부재, 여백 7087/5669(상·하) 등 정본값 확인 → 실COM `Open(path, 'HWPX', '')` → `SaveAs(pdf, 'PDF', '')` → PyMuPDF로 1쪽 PNG 렌더 → PNG를 직접 열어 글리프·여백 육안 확인

- [ ] **Step 5: 결과 기록·커밋** — §11에 "11-10. 웨이브 1 실행 결과" 표(과제·판정·증거) 추가, `verification-log.md`에 실행 명령·결과 추가 / 메시지 `Track F: 웨이브 1 검증 결과 기록`

---

### Task 9: F-1a 릴리스 준비 → 최종 확인 → 외부 반영

**Files:**
- Create(gitignore): `tests/out/track-f/check_exe.py`, `tests/out/track-f/release_notes.md`

- [ ] **Step 1: exe 동일성** — `git hash-object dist/anyway_to_hwpx_gui.exe`와 `git ls-tree c5438a8 dist/anyway_to_hwpx_gui.exe`의 blob 해시 일치 확인, SHA-256·크기는 `check_exe.py`에서 `hashlib`로 계산해 기록

- [ ] **Step 2: E-7 포함 판독(실행 없이)** — `check_exe.py`

```python
import hashlib
import sys
import types
from pathlib import Path
from PyInstaller.archive.readers import CArchiveReader

sys.stdout.reconfigure(encoding="utf-8")
exe = Path("dist/anyway_to_hwpx_gui.exe")
print("size", exe.stat().st_size, "sha256", hashlib.sha256(exe.read_bytes()).hexdigest())
archive = CArchiveReader(str(exe))
pyz_name = next(name for name, entry in archive.toc.items() if entry[-1] == "z")
code = archive.open_embedded_archive(pyz_name).extract("anyway_to_hwpx_com")


def names(co):
    found = set(co.co_names) | {c for c in co.co_consts if isinstance(c, str)}
    for const in co.co_consts:
        if isinstance(const, types.CodeType):
            found |= names(const)
    return found


print("HSecDef" in names(code))
```

판정: `True`(E-7 경로 포함)

- [ ] **Step 3: 릴리스 노트 초안** — `tests/out/track-f/release_notes.md`: 포함 수정(E-7 PDF layout 여백, UPX 재압축), 크기·SHA-256, 요구 사항(Windows·한컴오피스), 직전 릴리스 대비 변경

- [ ] **Step 4: 최종 확인 요청(사용자)** — 한 번에 제시: ① `feature/track-f-wave1` → `main` `--no-ff` 병합 후 push할 커밋·파일 목록 ② 릴리스 태그(권장 `v2026.08.27` → `c5438a8`)·제목·노트·자산 ③ exe 기동 smoke(사용자 직접 실행 또는 5초 기동 실행 승인) ④ 상위 `~/.claude` 서브모듈 포인터는 변경하지 않음

- [ ] **Step 5: 승인 후 실행·재조회** — `git switch main` → `git merge --no-ff feature/track-f-wave1` → `git push origin main` → `gh release create <태그> dist/anyway_to_hwpx_gui.exe --target c5438a8 --title ... --notes-file tests/out/track-f/release_notes.md` → `gh release view <태그>`·`git ls-remote --tags origin`으로 태그·자산·크기 재조회, 결과를 §11-10에 기록
