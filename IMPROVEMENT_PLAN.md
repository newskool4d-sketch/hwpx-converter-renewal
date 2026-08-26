# HWPX Converter Renewal — 정밀 분석 및 개선 방안

> 작성일: 2026-06-29
> 분석 대상: `C:\Users\홍주형\.claude\hwpx-converter-renewal`
> 기준 정본: `G:\내 드라이브\06 Obsidian Vault\00_공통규칙\HWPX_작성규칙.md` (최초 2026-03-22)
> 초점: ① 공공기관 작성 방향 강화 ② 표 내용·성격 기반 자동 폭 조절

---

## 0. 결론 요약

| 영역 | 진단 | 강도 |
| :-- | :-- | :-- |
| 표 폭 자동 조절 | **정본 §8-4를 코드가 부분만 이행** — 역할(성격) 분류는 하나 "실제 내용 길이 2차 보정"을 역할 매칭 표에서 건너뜀 | 🔴 핵심 |
| 표 헤더 음영색 | 활성 경로가 `#E7E7E7`(밝음) — 정본 §8-2는 RGB 200(`#C8C8C8`) | 🟠 중 |
| 줄 간격 160% | 정본 §7-3 규정 있으나 코드 미적용 | 🟠 중 |
| 금액 한글 병기 | 정본 §1-2 규정 있으나 미구현(날짜만 정규화) | 🟡 보조 |
| 아키텍처 | 모놀리스 내 표 후처리 중복·dead code, GUI 소스(.py) 워크트리 부재 | 🟡 정리 |

> **핵심 메시지**: 사용자가 요청한 "내용·성격에 따른 자동 폭 조절"은 신규 기능이 아니라 **정본이 이미 규정한 동작(§8-4 적용원칙 1·2·3)을 코드가 완전히 이행하도록 교정**하는 작업이다. 이 프레이밍이 가장 정확하다.

---

## 1. 시스템 구조

```
anyway_to_hwpx_com.py  (2,681줄, CLI 변환 엔진 = 모놀리스)
 ├─ 파싱:  md / txt / html / csv / xlsx / docx / pdf → 공통 block 리스트
 ├─ 빌드:  build_doc() → HWP COM(HWPFrame.HwpObject)으로 본문·표 삽입
 └─ 후처리(HWPX zip XML 재작성):
        apply_official_page_margins()      여백
        apply_table_layout_profiles()  ──► table_hwpx_postprocess (모듈)
        apply_list_hanging_indents()       항목 내어쓰기
        fix_body_text_prid()

표 레이아웃 모듈군 (분리됨):
        hwpx_layout.py            폭·행높이·여백 계산 (content-aware 엔진)
        table_roles.py            역할 추론 + 역할별 폭 프로파일
        table_model.py            TableLayout 조립
        table_grid.py             병합셀 격자 전개
        table_hwpx_postprocess.py 활성 표 후처리(폭·음영·병합·여백)
        table_hwpx_styles.py      borderFill(테두리·음영) 생성
```

**변환 파이프라인 (`convert_file`)**:
`parse → (insert_end_mark 시) 날짜정규화·끝표시 → COM build_doc → SaveAs → XML 후처리`

---

## 2. 표 폭 자동 조절 — 핵심 진단

### 2-1. 정본이 요구하는 동작 (§8-4)

> "열 너비는 **열의 성격(역할)**에 따라 차등 설정한다. **고정 비율이 아니라** 아래 분류 원칙을 우선 적용하고, **실제 내용 길이로 보정**한다."
>
> 적용 원칙
> 1. 헤더 키워드로 1차 분류 → **실제 열 내용의 최대 길이로 2차 보정**
> 2. 같은 성격 열이 여러 개이면 **내용 길이 비례**로 균형 배분
> 3. 한 열이 전체를 독식하지 않도록 **최대 글자 수에 상한(30자)** 적용

| 정본 열 성격 | 헤더 예시 | 너비 기준 |
| :-- | :-- | :-- |
| 연번·식별 | 순, 번, 번호, 코드 | 8~10% |
| 구분·분류 | 구분, 항목, 유형, 종류, 단계, 주체 | 15~20% |
| 보조 정보 | 비고, 근거, 조항, 책임 귀속, 위치 | 20~25% |
| 본문 내용 | 내용, 주요 내용, 결론, 권고 내용, 처리 방법 | 40~65% |

### 2-2. 코드의 실제 동작 (`table_roles.py:191 table_widths_for`)

```python
def table_widths_for(header, rows, table_role, col_count, total_width):
    profile = _role_profile(table_role, col_count)
    if profile:
        return _scale_profile(profile, total_width)   # ← 여기서 즉시 반환
    calculated = calc_col_widths(header, rows, total=total_width)
    return _clamp_widths(_expand_long_text_width(calculated, ...), ...)
```

- **역할이 매칭되면 `_scale_profile`(고정 비율)을 즉시 반환** → 정본 §8-4 "2차 보정"을 **건너뜀**.
- content-aware 엔진(`calc_col_widths` → `_infer_col_kind` → `_content_preferred_width`)은 **역할 미매칭 표에서만** 작동.
- 증거: `test_table_quality_port.py:171` — 매우 짧은 budget 표(`["강사료","2명 x 2시간","400,000원"]`)가 내용과 무관하게 항상 `[2400, 5000, 2600]`(24:50:26 고정)을 받음.

> **즉, '성격(역할) 감지'(`infer_table_role`)는 잘 동작하나, 사용자가 지적한 '내용 보정'이 정확히 역할 매칭 경로에서 죽어 있다.** 이것이 사용자 요청의 정중앙이다.

### 2-3. 부차 문제

- `hwpx_layout.py`의 `COLUMN_PROFILES`는 절대 HWPUNIT(min/pref/max)를, `table_roles.py`의 `ROLE_WIDTH_PROFILES`는 백분율을 쓴다 → **두 개의 폭 체계가 공존**하고 정본 §8-4의 4분류 백분율 밴드와도 정렬되지 않음.
- 정본 §10은 폭 산정 메커니즘을 명시적으로 `calc_col_widths(header, rows)`로 규정 → **역할 프로파일 레이어가 정본이 문서화한 메커니즘 자체를 우회**하고 있음.

### 2-4. 재설계안 — "프로파일=사전(prior)·경계(bounds), 내용=목표(target)"

역할 프로파일을 폐기하지 않는다. 문서 전체에서 같은 종류 표가 들쭉날쭉해지는 것을 막는 **시각적 일관성**도 공문서의 가치이기 때문이다. 대신 프로파일을 **고정값이 아닌 경계로** 전환한다.

```
1. content = calc_col_widths(header, rows, total)          # 내용 측정(이미 존재)
2. role 매칭 시 profile_w = _scale_profile(profile, total) # 역할 사전
3. 각 열의 허용 밴드 [min_i, max_i] 산출
       - 1순위: 정본 §8-4 성격별 백분율(연번 8~10 / 구분 15~20 / 보조 20~25 / 본문 40~65)
       - 2순위: profile_w[i] ± 허용오차(tolerance, 예: ±35%)
4. target_i = clamp(content_i, min_i, max_i)
5. 합계를 total에 맞춰 본문 내용 열 우선 재분배(_redistribute_to_bounds 재사용)
6. 본문 내용 열 상한 = 정본 §8-4 note3 "30자" → 시각폭 60units 상한 반영
```

- 효과: budget 표에서 `산출내역`이 짧으면 50%를 다 먹지 않고 내용에 맞게 축소, 길면 상한(65%)까지 확장.
- 튜닝 파라미터: `tolerance`(프로파일 결속 강도), 성격별 백분율 밴드 → 상수로 노출.
- `_infer_col_kind`의 9종 kind를 정본 4분류로 매핑하는 표를 추가해 §8-4와 1:1 정렬.

> ⚠️ 이 재설계는 `test_table_model_profiles.py`·`test_table_quality_port.py`의 **정확값 계약(exact width)을 설계상 변경**한다. 회귀가 아니라 계약 재기준화(re-baseline)이며, 새 계약은 "밴드 내 단조성·합계 보존·성격별 상하한 준수"로 재작성해야 한다.

---

## 3. 공공기관 작성 방향 — 정본 ↔ 코드 대조

| 정본 항목 | 근거 | 코드 현황 | 판정 |
| :-- | :-- | :-- | :-- |
| 본문 휴먼명조 13pt | §7-1 | `set_char_shape height=1300 휴먼명조` | ✅ |
| 표 맑은고딕 12pt | §7-1 | `height=1200 맑은 고딕` | ✅ |
| H1/H2/H3 16/14/13pt 진하게 | §7-1 | heights {1600,1400,1300} bold | ✅ |
| 페이지 여백(25/20/25/10/10mm) | §7-2 | `_OFFICIAL_PAGE_MARGINS` | ✅ |
| 날짜 `2026. 3. 22.` | §1-2 | `normalize_official_dates` | ✅ |
| 항목 8단계(1.→가.→…→㉮) | §2-1 | `OFFICIAL_LIST_PATTERNS` | ✅ (단, 아래 주의) |
| 항목 내어쓰기·2타 이동 | §2-2 | `apply_list_hanging_indents` + `official_list_para_shape` | ✅ |
| 붙임 표시·연속항목 | §3 | `_detect_attachment_head` + `attachment` block | ✅ |
| "끝" 표시(본문/표/이하빈칸) | §4 | `append_end_mark_blocks` | ✅ |
| 표 헤더 회색·가운데·진하게 | §8-2 | 음영 적용되나 **색 `#E7E7E7`** | 🟠 정본은 RGB 200(`#C8C8C8`) → 더 진해야 |
| **줄 간격 160%** | §7-3 | 미적용(line spacing 미설정) | 🟠 미준수 |
| **금액 한글 병기** | §1-2 | 미구현 | 🟡 미준수 |
| 단락 앞/뒤 간격(H1 5/2.5pt 등) | §7-3 | `set_para_shape`에 전달하나 **COM이 SpaceBefore/After 무시**(주석 명시) | 🟠 실효성 의문 |

### 3-1. 공공기관 강화 포인트(정본 근거 있음)

1. **표 헤더 음영색 정렬** — 활성 경로 `table_roles.HEADER_FILL_COLOR = 0xE7E7E7`을 정본 §8-2의 `0xC8C8C8`로. (참고: 모놀리스 dead code `_TABLE_HEADER_FILL_COLOR='#C8C8C8'`가 오히려 정본과 일치 — 활성 경로가 밝은 쪽으로 드리프트함.)
2. **줄 간격 160% 강제** — `set_para_shape` 또는 XML 후처리에서 `lineSpacing type="PERCENT" value="160"` 적용. 정본 §7-3 전 수준 공통.
3. **금액 한글 병기 정규화** — `normalize_official_dates`와 동일 패턴으로 `금113,560원(금일십일만…)` 변환기 추가. 정본 §1-2 + §9-3(예산 표기 준수).
4. **단락 간격 실효화** — COM이 무시하는 SpaceBefore/After를 XML 후처리(`paraPr` margin)로 실제 반영하거나, 현재 `_blank_line` 방식의 한계를 문서화.

### 3-2. 항목체계 주의(설계 판단 필요)

- 정본 §2-1 8단계는 **`1.`에서 시작**한다. 코드 `OFFICIAL_LIST_PATTERNS`는 depth 0에 **`Ⅰ.`(로마숫자)**를 추가로 둠 → 시행문 본문 기준 8단계보다 한 단계 위 레벨.
- 로마숫자 대제목은 계획서·보고서에서는 관행이나, **대외 시행문에서는 비표준**. 문서 유형(시행문 vs 계획서)에 따라 분기하거나, 최소한 옵션화 검토 권장.

### 3-3. 스타일 린트(선택, 비강제)

- 정본 §1-1: "'및' 자제 → '와/과/·'", "전문용어 지양". 변환기로 강제 불가하나 **경고(conversion note)** 수준의 린트 추가 가능.

---

## 4. 아키텍처 정리

| 항목 | 발견 | 권고 |
| :-- | :-- | :-- |
| 중복 표 후처리 | 모놀리스에 `apply_table_header_shading`(2036), `apply_table_cell_merges`(2090) 등이 모듈(`table_hwpx_postprocess`)과 별도로 존재 | 활성 경로(모듈)로 일원화 |
| dead code | `apply_table_header_shading`은 어디서도 호출 안 됨(파이프라인·테스트 모두) → **완전 사장** | 제거 후보(사용자 승인 후) |
| 테스트만 남은 함수 | `apply_table_cell_merges`는 `convert_file` 미사용이나 `test_core.py:942`가 호출 → **운영상 dead, 테스트 커버됨** | 병합을 모듈로 통합하고 테스트도 모듈 대상으로 이전 |
| 헤더색 분기 | `#C8C8C8`(dead)·`#E7E7E7`(active) 2색 공존 | §3-1 1번으로 단일화 |
| **GUI 소스 부재** | `anyway_to_hwpx_gui.py`가 워크트리에 **없음**(.spec과 빌드된 `dist\*.exe`만 존재) | 🔴 빌드 재현성 리스크 — 소스 복원·커밋 필요 |
| 폭 체계 이원화 | `COLUMN_PROFILES`(절대값) vs `ROLE_WIDTH_PROFILES`(백분율) | §2-4 재설계에서 정본 4분류로 수렴 |

> dead-code 판정은 GUI 래퍼·테스트까지 grep으로 교차 확인함. `apply_table_header_shading`은 호출처 0건, `apply_table_cell_merges`는 테스트 1건만. GUI는 `.py` 소스가 부재해 직접 검증 불가하나, exe는 `convert_file`을 호출하는 Tkinter 래퍼이므로 모놀리스 파이프라인 분석이 유효.

---

## 5. 개선 우선순위 로드맵

### Phase 0 — 레퍼런스 역산(기준값 확보, Phase 1 선행)
> 목적: §2-4의 밴드·상수를 **임의 수치가 아닌 사용자 직접 수정본에서 역산**해 ground-truth로 고정.

대상(정본 §11, 위치 확인 완료):
`G:\…\06 Obsidian Vault\03_프로그램\체험교육 프로그램\04 읽걷쓰기반생태독서캠프\`
- `02_학부모동의서.hwpx` (양식) · `03_출석인정공문.hwpx`(표 2개) · `04_활동결과발송공문.hwpx`(공문) · `05_참가신청서.hwpx`(표 5개)

추출 항목(HWPX zip XML 파싱, COM 불요):
1. **열 폭** — `hp:tbl/hp:sz` 대비 각 `hp:tc/hp:cellSz@width` → 백분율 환산 → 정본 §8-4 4분류 실제 밴드 캘리브레이션.
2. **헤더 음영색** — `header.xml` borderFill `winBrush@faceColor` → `#C8C8C8` vs `#E7E7E7` 실측 확정.
3. **페이지 여백·줄 간격** — `secPr/pagePr/margin`, `paraPr/lineSpacing@value`(160% 여부 실측).
4. **단락 간격** — 제목/본문 `paraPr@spaceBefore/After` 실값.

산출물: `reference_metrics.md`(추출 표).

**▶ Phase 0 실행 결과(2026-06-29, 완료)** — 전제와 다름:
- 4개 파일 전 표가 **균등 분할**(50:50 / 20×5 / 16.7×6 / 25×4) → 내용 적응형 폭 ground-truth **아님**(양식·출결부 성격).
- **헤더 음영 전무**, **줄간격·단락간격 설정값 없음**, 페이지 여백 = **HWP 기본값(20/15/30/30/15/15mm)**.
- ∴ 폭 밴드·헤더색·줄간격의 권위 기준은 **레퍼런스 HWPX가 아니라 작성된 정본 텍스트**(§8-4·§8-2·§7-3).
- Phase 0를 선행한 효과: **잘못된 소스 캘리브레이션을 사전 차단**. Phase 1은 정본 §8-4 백분율을 직접 밴드로 채택, 최종 확정은 육안 검수.
- (선택) 사용자가 실제 데이터 표 예시 문서를 지정하면 재캘리브레이션 가능.

### Phase 1 — 표 폭 정본 준수(핵심, 사용자 요청 직결) ✅ 완료(2026-06-29, TDD)
1. ✅ `table_roles.table_widths_for` 재작성 — 역할 매칭 시 즉시 반환 대신 `_blend_profile_with_content`로 내용 보정.
2. ✅ **비대칭 밴드** 채택(`ROLE_BAND_SHRINK=0.15`, `ROLE_BAND_GROW=0.30`) — 구조 열은 §8-4 하한 보호(보수적 축소), 본문 열은 내용 따라 확장(관대).
   - 설계 변경: 계획의 "9 kind→4 분류 명시 매핑"은 **미채택**. 비대칭 프로파일 밴드가 §8-4 의도(구분 15~20% 보호·본문 40~65%)를 암묵적으로 달성하여 복잡도↓. (명시 매핑은 추후 정밀화 시 재고)
3. 본문 30자 상한 — `_content_preferred_width`의 기존 detail 90units 상한 + 밴드 상한(+30%)으로 갈음. 별도 강제 미추가.
4. ✅ 계약 재기준화 — `tests/test_table_width_bands.py` 신설(반응성·합계·밴드캡 4건). 기존 정확값 budget 테스트 → 속성 계약, task_matrix 상한 5600→6500(§8-4), comparison 구분 하한 1200→1000.

**검증**: `python -m unittest discover -s tests` → **118 passed**(기존 114 + 신규 4). `py_compile` 통과. (한글 HWP 육안 렌더 검수는 Windows+HWP 필요 — 미실시.)

### Phase 2 — 공공기관 서식 강화 ✅ 대부분 완료(2026-06-29, TDD)
5. ✅ 헤더 음영 `#E7E7E7` → `#C8C8C8`(`table_roles.HEADER_FILL_COLOR`, 정본 §8-2). 테스트 갱신.
6. ✅ 줄 간격 160% — **XML 후처리로 전환**(`apply_official_line_spacing`, header.xml `hh:paraPr`에 `hh:lineSpacing type=PERCENT value=160` 강제). 레퍼런스 HWP 출력 스키마와 동일 → 손상 위험 최소. 신규 테스트 2건. (COM 경로는 제거.) 시각 적용은 HWP open-test 권장이나 스키마 일치로 위험 낮음.
7. ✅ 금액 한글 병기(§1-2) — `_sino_korean_amount` + `normalize_official_amounts`, `--insert-end-mark` 모드 연결. 신규 테스트 7건.
8. ✅ 단락 간격 XML 후처리 실효화(2026-07-03) — `apply_official_paragraph_spacing`. 제목 H1~H3 앞/뒤 간격을 header.xml paraPr margin(hc:prev/next)에 반영(1pt=100 HWPUNIT). 본문 0/0. 제목이 본문과 paraPr 공유 시 오적용 방지로 skip. ✅ 로마숫자 레벨 옵션화(2026-07-03) — `--doc-type {plan,sihaengmun}`.

### Phase 3 — 아키텍처 정리 (부분 완료)
9. ✅ dead 클러스터 제거 — `apply_table_header_shading`·`_make_gray_border_fill`·`_TABLE_HEADER_FILL_COLOR`·고아 `import copy`(호출·테스트 0건).
   - ✅ **병합 일원화 + latent bug 수정**(2026-06-30): 활성 모듈 경로(`table_hwpx_postprocess`)가 anchor cellSpan만 설정하고 **피병합 셀을 제거하지 않아** 병합 표(html·xlsx·docx·pdf)가 malformed였음. `_remove_covered_cells` 추가로 수정. 중복 모놀리스 `apply_table_cell_merges` + `TableCellMergeTests` 제거, 모듈 대상 테스트 3건 신설(`test_table_merge_postprocess.py`).
   - ✅ out-of-range 병합 방어(2026-07-03) — `_filter_spans_to_grid`. 격자(열수·행수) 범위를 벗어나거나 크기가 비정상인 병합 span을 무시(구 모놀리스 skip 동작 복원). end-to-end 단위테스트 3건.
10. ✅ GUI 소스 — 사용자 확인: 본체 엔진은 `anyway_to_hwpx_com.py`이며 GUI `.py` 복원 불필요(해소). 작업 초점은 CLI 엔진 유지.

---

## 6. 리스크·검증 기준

- **계약 테스트 변경**: Phase 1은 기존 exact-width 테스트를 의도적으로 깨뜨림 → "회귀 아님, 재기준화"임을 커밋·핸드오프에 명시.
- **COM 무검증 영역**: 폭·음영은 XML 후처리로 반영되므로 COM 없이 `python -m unittest discover -s tests`로 검증 가능. 단, 한글 실제 렌더 육안 검수는 Windows+HWP 필요(현 핸드오프 미검증 항목과 동일).
- **완료 기준**: ① 짧은 budget/schedule 표가 내용에 따라 폭 축소됨을 단위테스트로 입증 ② 긴 내용 열이 §8-4 상한 내에서 확장 ③ 헤더색·줄간격·금액 정본 일치 ④ 전체 테스트 green(재기준화 반영).

---

## 7. 확정된 방향 (2026-06-29 사용자 결정)

본 문서는 **분석·계획**이며 코드는 변경하지 않았다(사용자 규칙 §7). 착수 방향이 다음과 같이 확정됨:

| 결정 항목 | 확정 |
| :-- | :-- |
| 표 폭 재설계 강도 | **밴드 방식** — 프로파일=경계, 내용=목표(§2-4) |
| 계약 테스트 | **재기준화 동의** — exact width → 밴드·단조성·합계·성격별 상하한 검증 |
| 로마숫자 레벨(Ⅰ.) | **옵션화** — 문서 유형(시행문 vs 계획서·보고서)에 따라 on/off 분기 |
| GUI 소스 부재 | **복원 포함** — Phase 3에서 `anyway_to_hwpx_gui.py` 복원·커밋 |

### 착수 전 잔여 확인
- 본 작업은 사용자 규칙 §7(다단계 계획 우선)·§3(대량·고위험은 명시 지시 시)에 따라 **구현 착수는 별도 지시**로 진행한다.
- 구현 순서: **Phase 0(레퍼런스 역산)** → Phase 1(표 폭 정본 준수) → Phase 2(서식 강화) → Phase 3(아키텍처 정리).
- Phase 0는 읽기 전용 추출(COM 불요)이므로 즉시 착수 가능하며, 그 산출(`reference_metrics.md`)이 Phase 1 목표값을 고정한다.
- Phase 1 착수 시 `superpowers:test-driven-development`(프로젝트 §4 개발 스킬 순서)로 계약 재기준화 테스트부터 작성.

---

## 8. Track C 서식 개선 완료 (2026-07-03, TDD)

브랜치 `feature/track-c-format-improvements`. 4개 항목 test-first 구현, 전체 **153 tests green**, py_compile OK.

| # | 항목 | 구현 | 정본 | 테스트 |
| :-- | :-- | :-- | :-- | :-- |
| ① | 공공언어 스타일 린트 | `lint_official_style` — 순화 표현·'및' 경고(비강제, 텍스트 미수정), '실시간' 오탐 가드 | §1-1 | test_official_style_lint (7) |
| ② | 로마숫자 레벨 옵션화 | `--doc-type {plan,sihaengmun}` + `detect_official_list_item(allow_roman)` + 글로벌 `_ALLOW_ROMAN_LEVEL` | §2-1 | test_roman_level_option (8) |
| ③ | 병합 격자 방어 | `_filter_spans_to_grid` — 범위 초과·비정상 span 무시(구 모놀리스 skip 복원) | §8 | test_table_merge_postprocess (신규 7) |
| ④ | 제목 단락 간격 | `apply_official_paragraph_spacing` — H1 5/2.5·H2 4/2·H3 3/1.5pt(1pt=100 HWPUNIT), 본문 0/0. 공유 paraPr은 레벨별 clone·재배정으로 **전면 적용**(2026-07-03) | §7-3 | test_official_paragraph_spacing (9) |

### HWP 실변환 검수 결과 (2026-07-03)

헤딩·목록·표·공문 표현을 담은 문서를 `--insert-end-mark`로 실제 HWP COM 변환하여 확인:
- ✅ **④ 단락 간격 실발화 확인** — 배타적 H3 paraPr 2건에 `prev=300 next=150`(§7-3 H3 3/1.5pt) 적용. H1은 본문과 paraPr 공유(pp0)로 안전 skip + 참고 로그 1건. **핵심 잔여였던 "COM paraPr 배정" 의문 해소**: 배타 시 적용·공유 시 무해 skip이 실측 확인됨.
- ✅ **① 스타일 린트** — CLI에 순화 경고 3건(금일·향후·및) 표시. (검수 중 `main()`이 notes를 미출력하던 결함 발견·수정.)
- ✅ **부수 정규화** — 금액 한글병기(`금400,000원(금사십만원)`)·"끝" 표시·항목기호 정상.

### 잔여 (선택, HWP 육안)
- ✅ **② 로마숫자 실변환 검증(2026-07-03)**: `--doc-type sihaengmun`에서 `1.` 들여쓰기 left=900(depth1)→**620(depth0)**, `가.` 1320→960로 당겨짐을 출력 XML로 확인. 정본 §2-1대로 발화.
- ✅ **④ 전면 적용(2026-07-03)**: 공유 paraPr을 레벨별 clone하여 제목에만 재배정(본문 0/0 보존). HWP 실변환 검증 — H1 500/250·H2 400/200·H3 300/150이 clone(pp20/21/22)에 적용됨. TDD 중 파일 라운드트립 버그(section0.xml 미기록) 발견·수정. (기존 skip 방식 → clone 방식 재기준화)
- 공통: 렌더 육안 검수는 Windows+HWP 필요. XML 스키마/값 수준은 `python -m unittest discover -s tests`(153 green)로 검증됨.

---

## 9. Track D kordoc 연계 개선 완료 (2026-07-12, TDD)

kordoc(v4.0.5) 업그레이드 후 참고 사항을 대조해 4개 항목 반영. 전체 **237 passed, 1 skipped**(bs4 미설치). 정본(`HWPX_작성규칙.md`)에 §8-6 신설.

| # | 항목 | 구현 | 정본 | 테스트 |
| :-- | :-- | :-- | :-- | :-- |
| ① | 표 테두리 매트릭스 | `positional_border_spec` — 셀 위치(병합 span 범위)별 borderFill 배정. 외곽 SOLID 0.4mm·내부 0.12mm·헤더 하단 DOUBLE_SLIM 0.5mm(본문 1행 상단 미러링). 1행/1열 표는 외곽선 우선 | §8-6(신설) | test_table_border_matrix (9), test_table_quality_port 갱신 |
| ② | 셀 좌우 안여백 | `TableCellStyle.margin_left/right` 170→510(1.8mm) — kordoc 실측 대조 | §8-6 | test_table_quality_port |
| ③ | 라운드트립 내용 검증 | `scripts/roundtrip_verify.py` — md→HWPX(COM)→md(kordoc CLI) 후 표 셀·문단 텍스트 보존 대조. COM·CLI 필요로 기본 스위트 제외(scripts/) | — | 음성 대조 자체검증 |
| ④ | '천원' 축약 린트 | `lint_money_notation` — 숫자+천원 패턴 경고(표 셀까지 스캔, `lint_official_style`과 분리). '수천원' 오탐 가드 | §1-2 | test_official_style_lint (신규 5) |

### HWP 실변환 검수 결과 (2026-07-12)
- ✅ **① 테두리 실발화**: 4×4 표 출력 XML에서 헤더행(top 0.4mm·bottom 이중선·#C8C8C8) / 본문 1행 top 이중선 미러링 / 중앙 셀 전부 0.12mm / 마지막 행 bottom 0.4mm 확인. 1행 표는 하단이 이중선 아닌 외곽 0.4mm(엣지 케이스).
- ✅ **③ 라운드트립**: 번들 샘플 토큰 18/18 보존, 음성 대조로 누락 탐지 동작 확인.
- ✅ **④ 천원 린트**: `--insert-end-mark` 실변환 시 표 셀 "400천원"에 대해 경고 발화(금일·및과 함께).

### 보류 — 서식 프로필 추출·재현 (후속 아이디어)
- kordoc `extract_profile`(참조 HWPX → 테두리·음영·열폭·셀 글꼴 JSON)의 이식을 검토했으나, **§8-6이 테두리·음영을 전 표 표준 적용**하고 글꼴은 정본 §7-1(맑은고딕)로 이미 고정되어 대부분 subsume됨. 남은 고유 가치는 참조 문서별 **열폭 프로필**뿐이며, 현재 `TABLE_HEADER_WIDTH_PROFILES`(헤더 키워드) + 내용 길이 자동 산정으로 충분.
- 착수 시 후보: (a) `scripts/extract_width_profile.py`로 참조 HWPX에서 헤더→열폭 비율 JSON 추출(개발 도구, 핫패스 무변경), (b) `TABLE_HEADER_WIDTH_PROFILES` 외부 JSON 병합(런타임 사용자 프로필). **2026-07-12 사용자 결정: 이번 회차 보류.**

---

## 10. Track E 차기 개선 (2026-08-26 수립·대부분 실행 완료)

> 기준 시점 현황: 유닛 테스트 **243 passed, 1 skipped**(2026-08-26 재실행 확인). Phase 0~3·Track C·D 완료, 한컴 호환 선언부 복원(08b2130)·GUI exe 재빌드(c6e91df) 반영 완료.
> 실행 결과: E-1~E-4·E-7 완료(TDD 회귀 수정 1건 포함). E-5(보류)·E-6(미착수)은 남음.

### 10-1. 잔여·후보 과제 목록

| # | 과제 | 출처 | 난도 | 상태 |
| :-- | :-- | :-- | :-- | :-- |
| E-1 | **UPX 재설치 후 exe 재압축** — 현재 77.5MB(UPX 스킵), 재압축 시 ~70MB 복귀. 검증: 기동 smoke + CArchive 판독 | c6e91df 커밋 메시지 | 하 | ✅ 완료(2026-08-26) — 73,746,619 bytes(70.3MB), 기동 smoke 통과 |
| E-2 | **COM 의존 잔여 검증 재개** — `--preflight` 통과 환경에서 `HWPX_RUN_COM_TESTS=1`로 `test_pdf_hwp_com_integration.py` 실행(PDF→HWPX→PDF native round-trip) | handoff.md "재개 시 다음 액션" | 하 (환경 의존) | ✅ 완료(2026-08-26) — 테스트 API 호출 결함 2건 수정 + E-7 근본 원인 수정 후 **최초로 green**(1584.6s) |
| E-3 | **편집기 안전성 게이트 정례화** — 08b2130에서 1회성으로 쓴 python-hwpx 6.0.2 `editor_safety_gate --strict`를 `scripts/`에 상설화, 실변환 검수 절차에 포함 | 08b2130 검증 절차 | 하 | ✅ 완료(2026-08-26) — `scripts/hwpx_editor_safety_gate.py`, 번들 샘플 2종 PASS |
| E-4 | **스테일 QA 잔재 정리** — `native-qa.txt`(mojibake 경로의 구 실패 로그, 현재 GUI 소스 존재로 무효) 삭제 또는 재실행 결과로 갱신, skip 1건(bs4) 처리 방침 결정(requirements 추가 vs skip 유지 명문화) | native-qa.txt·테스트 스위트 | 하 | ✅ 완료(2026-08-26) — 7개 상태 재실행 exit 0으로 갱신. skip 1건(bs4) 방침은 미결(하단 비고) |
| E-5 | **서식 프로필 추출·재현** — §9 보류 항목 재개: (a) `scripts/extract_width_profile.py` (b) `TABLE_HEADER_WIDTH_PROFILES` 외부 JSON 병합 | §9 보류(2026-07-12) | 중 | 보류 유지 — 사용자 재결정 필요 |
| E-6 | **PDF editable 환경 안내 강화** — Java 11 미만이면 opendataloader-pdf 불가·fallback 사용 중(현 환경 Java 8). 요건·품질 차이를 README·GUI 안내에 명시 | 테스트 실행 중 실측 경고 | 하 | 미착수 |
| E-7 | **PDF layout 모드 SaveAs 왕복 시 콘텐츠 위치 어긋남** — E-2 COM 검증 중 신규 발견(§10-4) | E-2 실행 중 발견(2026-08-26) | 중 | ✅ 완료(2026-08-26, TDD) — `configure_pdf_page_setup()` 근본 원인 수정, 실COM round-trip 최초 green |

### 10-2. 권장 실행 순서·완료 기준

1. **1차 묶음(E-1·E-3·E-4)**: COM 불요·저위험 위생 작업. 완료 기준 — ① exe 크기 ≤71MB + 기동 smoke 통과 ② `editor_safety_gate` 스크립트가 번들 샘플 산출물에서 exit 0 ③ 스테일 로그 제거·skip 방침이 문서에 명문화됨. **→ 2026-08-26 전부 충족(①②③)**, 단 skip 방침 명문화는 미완(하단 비고).
2. **2차(E-2)**: HWP COM 정상 응답 환경에서만. 완료 기준 — preflight OK + COM 통합 테스트 green, 결과를 verification-log.md에 기록. **→ 전부 충족(2026-08-26)**. preflight OK, E-7 근본 원인 수정 후 COM 통합 테스트가 이 테스트가 생성된 이래 최초로 green(1584.6s), verification-log.md 기록 완료.
3. **3차(E-5·E-6)**: 기능 확장. E-5는 §9 보류 결정의 재확인이 선행 조건 — **사용자 승인 전 착수 금지**.

### 10-3. 비고

- E-1 exe 재빌드는 사용자 승인(winget UPX 설치) 후 진행함. E-4는 삭제 대신 **재실행 결과로 갱신**하는 방식을 택해 파일 삭제를 회피함.
- skip 1건(bs4 미설치)의 처리 방침은 이번 회차에서 결정하지 않음 — 다음 착수 시 재확인.
- 표 폭·서식 로직은 정본(§8-4·§8-6·§7-3) 준수 상태로 판단했던 전제는 유지되나, **PDF 레이아웃 모드의 왕복 재추출 경로**에서 신규 결함이 발견되어 아래 E-7로 등록함.

### 10-4. E-7 (신규, 2026-08-26 발견·해결) — PDF layout 모드 SaveAs 왕복 시 콘텐츠 위치 어긋남

> **상태: ✅ 해결(2026-08-26, TDD).** 아래는 발견 당시 기록 + 근본 원인·수정 내역.

- **증상**: `PDF → HWPX(layout 모드) → HWP SaveAs 'PDF'` 왕복 시, 원본과 재추출 PDF의 비백색 콘텐츠 경계가 우측·하단으로 균일하게 약 84~98pt 이동. 콘텐츠 박스 크기 자체는 거의 보존(449×181 → 439×183).
- **격리된 사실**: `configure_pdf_page_setup()`(anyway_to_hwpx_com.py:2351)이 여백을 전부 0으로 설정하고, HWPX 산출물 자체의 구조 계약(`pic`/`orgSz`/`curSz`/`sz`, pagePr)은 기존 COM 테스트(`_assert_hwpx_image_contract`)가 별도로 통과시킴 → **HWPX 산출물 구조는 정상으로 보이며, 어긋남은 HWP `SaveAs('PDF', '')` 재추출 단계 또는 `InsertPicture` 앵커 위치 자체**에서 발생하는 것으로 추정(근본 원인 미확정).
- **왜 지금까지 미검출**: `tests/test_pdf_hwp_com_integration.py`는 `HWPX_RUN_COM_TESTS=1` 게이트 뒤에 있고, handoff.md 기록상 과거 모든 세션이 COM timeout으로 실행 자체를 건너뜀 — **2026-08-26이 이 테스트의 최초 실행**.
- **선행 조치 완료**: 테스트 자체의 API 호출 결함 2건(`hwp.Open`·`hwp.SaveAs` 인자 개수 부족 — 실제 COM 타입라이브러리는 `Open(filename, Format, arg)`/`SaveAs(path, Format, arg)` 3-인자 필수)을 수정해 테스트가 실제 round-trip까지 도달하도록 만듦. 이 수정 자체는 변환기 코드 무변경(테스트 파일만).
- **근본 원인(확정)**: `configure_pdf_page_setup()`이 쓰던 `hwp.CreateAction('PageSetup') → action.Execute(parameter_set)` 경로는 여백(TopMargin 등) 변경에 대해 `Execute()`가 `True`(성공)를 반환하지만 **실제로는 반영되지 않는 HWP COM 동작**이었다. 같은 세션에서 재조회하면 여백이 HWP 기본값(30/20/15/15mm)으로 그대로 남아 있었고, 이 기본 여백+헤더 영역(≈85pt+99pt)이 관측된 84~100pt 어긋남을 정량적으로 정확히 설명한다. `InsertPicture`가 삽입한 이미지 자체는 앵커 원점(0,0)에 정확히 배치돼 있었다(무죄).
- **수정**: `hwp.CreateAction` 경로 대신 **`hwp.HParameterSet.HSecDef` + `hwp.HAction.GetDefault/Execute('PageSetup', sec.HSet)`**(속성 접근 방식) 경로로 재작성 — 이 경로는 실COM에서 여백 변경이 실제로 지속됨을 직접 확인. `anyway_to_hwpx_com.py`의 `configure_pdf_page_setup()` 수정.
- **검증**: TDD로 `tests/test_pdf_hwp_image_writer.py`의 관련 계약 테스트 4건을 새 API 경로 기준으로 재작성(RED 확인 후 GREEN). 전체 COM-불요 스위트 243 passed 유지. 실COM `HWPX_RUN_COM_TESTS=1` 통합 테스트가 **테스트 생성 이래 최초로 green**(`test_generated_pdf_round_trips_through_hwp_image_pages`, 1584.6s).
- **재현/재검증**: `HWPX_RUN_COM_TESTS=1 python -m unittest tests.test_pdf_hwp_com_integration` (Windows + 한컴오피스 COM 필요).
