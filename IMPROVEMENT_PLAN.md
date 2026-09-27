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
- **정정(2026-09-27, Track F N14)**: 현 환경 skip 1건은 COM 통합 테스트 게이트(`HWPX_RUN_COM_TESTS` 미설정)이며 bs4 4.14.3 설치 확인 — 방침 결정 불요, 종결.
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

---

## 11. Track F — 신뢰성·배포 정상화 로드맵 (2026-09-27 수립·미착수)

> 기준: `main` `c5438a8`(= `origin/main`), 2026-09-27 실측. 본 절은 계획만 담고 코드는 변경하지 않음.
> 목표 상태: **"완료"로 표시된 변환 결과와 공개 배포본을 그대로 신뢰할 수 있는 변환기** — 조용한 실패 0건, 공개 최신 릴리스 = 검증된 `main`.
> 원칙: 요청 범위 최소 변경 · 하위 호환 추가형(additive) · 측정 전 성능 주장 금지 · 독립 리팩터링 트랙 없음(트랙이 요구하는 추출만).

### 11-1. 핵심 요약

| 순위 | 과제 | 한 줄 근거 | 규모(추정) | 승인 |
| :-: | :-- | :-- | :-: | :-: |
| 1 | F-1 릴리스·저장소 정상화 | 공개 최신 `v2026.08.06`(→ `c6e91df`)에 E-7 PDF 여백 수정 미포함 | 소 | L4 (D-1·D-2) |
| 2 | F-2 조용한 실패 제거 | 후처리·빌드 경고 10곳이 `print`만 사용 → `console=False` exe에서 소실 | 소~중 | L2 |
| 3 | F-3 옵션 정합성 | 공문 정규화가 `--insert-end-mark`에 결합, 문서유형은 CLI 전역 상태라 GUI 선택 불가 | 중 | L2 |
| 4 | F-4 실물 회귀 러너 | 실COM 회귀가 PDF layout 1건뿐 — 공문·계획서·병합 표 회귀 부재 | 중 | L3 |
| 5 | F-5 COM 세션 복구 | 인스턴스 1개로 배치 처리, 오염 시 잔여 파일 연쇄 실패 구조 | 소~중 | L2·L3 |
| 6 | F-6 Markdown 충실도 | 이미지 무통보 삭제, 인라인 강조 평문화 | 중 | D-4·D-5 |

### 11-2. 기준선 (2026-09-27 실측)

| 항목 | 값 | 근거 유형 |
| :-- | :-- | :-- |
| HEAD | `c5438a8` = `origin/main`, 미푸시 0 | 실측(git) |
| COM 불요 스위트 | 243 tests · skip 1(COM 통합 테스트 — `HWPX_RUN_COM_TESTS` 미설정 게이트) · 8.9s · OK / bs4 4.14.3 설치 확인 | 실측(unittest -v·import) |
| 모놀리스 | `anyway_to_hwpx_com.py` 3,023줄 · 함수 131개 · 최장 `parse_markdown` 140줄 | 실측(AST) |
| 모놀리스 외부 참조 표면 | 64개 심볼(tests·GUI·scripts·shim, 비공개 `_` 심볼·`time` 패치 포함) | 실측(AST) |
| 공개 릴리스 | 최신 `v2026.08.06` → `c6e91df`(자산 81,276,499 bytes). `main` 추적 exe는 73,746,447 bytes — 문서 기록 73,746,619와 172 bytes 차이, 릴리스 시 SHA-256으로 확정 | 실측(gh·git) |
| 저장소 | GitHub public · 393,158KB / 로컬 loose objects 844.60MiB / `dist/anyway_to_hwpx_gui.exe` 추적 중(이력 7개 버전, 73~88MB) | 실측(gh api·git) |
| 하류 호출자 | 전역 shim `~/.claude/to_hwpx_com.py` → `main()` / Claude 스킬 8종·Codex 스킬 1종(+ `.agents` 사본)이 CLI 사용(`-o`, `--insert-end-mark`) | 실측(Grep) |

### 11-3. 신규 진단

| ID | 발견 | 근거(유형 · 위치) | 영향 | 등급 |
| :-- | :-- | :-- | :-- | :-: |
| N1 | 공개 최신 릴리스가 `main`보다 3커밋 뒤처짐 — E-7(`19806ca`) 미포함 | 실측: tag `v2026.08.06` → `c6e91df` | layout 모드 PDF 변환 시 페이지 이미지가 HWP 기본 여백만큼 밀린 exe가 배포 중 | 🔴 |
| N2 | 후처리·빌드 경고의 GUI 소실 — 경고·참고 출력 10곳이 `print`만 사용, GUI는 `console=False`·스트림 리다이렉트 없음. 파싱 단계 note(`_add_conversion_note`)는 `result['notes']`로 GUI 도달 | 코드: `anyway_to_hwpx_com.py:1952·2031·2081·2217·2224·2250·2327`, `table_hwpx_postprocess.py:234·267·319`, `anyway_to_hwpx_gui.spec:92` / GUI 재현 미실시 | 서식 후처리 실패에도 GUI는 "완료" 표시. CLI는 출력되나 종료코드 0 → 하류 스킬은 성공 처리 | 🔴 |
| N3 | 변환 경로에 산출물 자가검증 없음 — 안전 게이트는 별도 스크립트(python-hwpx 의존) | 코드: `convert_file` 후처리 블록 `anyway_to_hwpx_com.py:2885-2894` | 구조 결함이 사용자 열람 시점까지 미검출 | 🟠 |
| N4 | 경고 피로 — `TableColWidth` 미지원 환경에서 표마다 재시도·경고. note는 수집 시 stdout, 종료 시 stderr로 CLI 중복 출력 | 코드: `:2315-2327`, `:859-861`·`:3003-3004` / 기록: `verification-log.md` 2026-06-09 | 실제 경고가 묻힘 | 🟡 |
| N5 | 공문 정규화(날짜·금액·린트)가 `--insert-end-mark`에 결합 | 코드: `:2829-2834` | "끝" 없이 정규화만 적용 불가, GUI "끝 표시" 체크박스 의미 불투명 | 🟠 |
| N6 | 문서유형이 모듈 전역(`_ALLOW_ROMAN_LEVEL`)·CLI 전용 | 코드: `:194·2969-2970` / `gui_conversion_worker.py` `ConversionSnapshot`에 필드 없음 | GUI에서 시행문 항목체계 적용 불가 | 🟠 |
| N7 | Markdown 이미지 무통보 삭제, 링크·강조 평문화 | 코드: `_clean_inline` `:127-137` | 보고서 그림 누락을 사용자가 인지 못 함 | 🟠 |
| N8 | COM 인스턴스 1개로 배치 처리, 오염 시 재생성 없음 / CLI `finally`의 `hwp.Quit()` 무보호 | 코드: `main` `:2972-3011`, `gui_conversion_worker.run_conversion` / 타 저장소 실측 기록(단일 인스턴스 도중 오염) / 본 저장소 미재현 | 대량 변환 시 연쇄 실패 | 🟠 |
| N9 | 시간 표기(정본 §1-2, 24시각제 `15:20`) 미구현 | 코드: 관련 로직 검색 결과 없음 | 정본 미준수 | 🟡 |
| N10 | exe 바이너리 git 추적 — `.gitignore`의 `dist/`와 모순 | 실측: `git ls-files dist`, `git log --stat` | 공개 저장소 비대·클론 비용 | 🟠 |
| N11 | Java 11 미만 안내가 영문 note 1줄(E-6 미착수) | 코드: `:1640-1649` | 사용자 조치 방법 불명 | 🟡 |
| N12 | 문서 스테일·경로 노출 — `handoff.md`(07-12), `dist/` 매뉴얼(05-28), 마스터 프롬프트 미추적(개인 경로 포함). 기추적 문서(본 파일 상단·`verification-log.md`)에도 사용자 절대경로 기공개 | 실측: ls·git status·Grep | 인계·안내 부정확, 추가 커밋 시 노출 확대 — 이후 추적 문서는 상대 경로만 | 🟡 |
| N13 | (범위 밖) `.agents` 스킬 2곳이 존재하지 않는 `%USERPROFILE%\.Codex\to_hwpx_com.py` 안내 | 실측: Grep·Glob | Codex 측 HWPX 변환 실패 가능 | 별도 과제 |
| N14 | 기록 오류 — §10-3·마스터 프롬프트의 "skip 1건 = bs4 미설치"가 현 환경과 불일치(실제 skip은 COM 게이트) | 실측: `unittest -v` skip 사유·`import bs4` | §10-3 미결 방침이 이미 해소됐는데 미결로 남음 | 🟡 |
| N16 | 한글 자동화 파일 접근 확인 창 — 동결 exe GUI로 `C:\tmp\…` 저장 시 "한글을 이용하여 위 파일에 접근하려는 시도" 확인 창 발생(사용자 폴더 하위 저장인 기존 CLI 실행에서는 미발생). 코드의 `RegisterModule('FilePathCheckDLL', 'SecurityModule')` 모듈명과 레지스트리 등록명(`FilePathCheckerModule`) 불일치 — 원인 가설, 미검증. 해당 호출은 공개 `v2026.08.06`(`c6e91df`)과 동일 — 회귀 아님. 같은 경로 CLI 비교는 다른 문서가 한글에서 사용 중인 시점과 겹쳐 판정 불가 | 실측: GUI 화면·레지스트리 읽기 / CLI 비교 재시험 필요 | 사용자 폴더 밖 저장 시 확인 창·저장 실패 가능(기존 동작으로 추정) | 🟡 |
| N16-보강 | (2026-09-28) 확인 창이 사용자 폴더 하위 저장(`tests/out/track-f/w2/`)에서도 발생 → 경로 의존 가설 기각. 레지스트리 `HKCU\Software\HNC\HwpAutomation\Modules`는 값 1개(`FilePathCheckerModule`)·마지막 수정 2026-04-12로 변동 없음 → 코드의 `'SecurityModule'` 등록은 줄곧 실패했을 가능성이 높음. 확인 창이 없던 실행은 다른 자동화 클라이언트가 띄운 한글 인스턴스를 공유했을 가능성(N18, 미검증) | 실측: 확인 창 화면·레지스트리 키 수정 시각 | 모든 변환이 확인 창에서 멈출 수 있음(무인 실행·하류 스킬) | 🔴 |
| N17 | 날짜 정규화가 마침표 없는 날짜 뒤 공백을 소실 — `2026.3.22 행사` → `2026. 3. 22.행사`(정규식 끝 `\s*\.?`) | 실측: 특성화 테스트(웨이브 2 Task 3) | 공문 정규화 사용 시 날짜와 뒷말이 붙음 | 🟠 |
| N18 | 동시 한글 자동화 — 검증 중 다른 클라이언트의 COM 인스턴스(`hwp.exe -Automation -Embedding`, 07:26:51)와 파일 직접 열기 인스턴스가 동시 실행. `Dispatch`가 기존 자동화 인스턴스에 붙으면 보안 모듈 상태·`Quit`이 서로 간섭할 수 있음(전날 "빈 문서 저장?" 창·타 문서 창 출현과 부합) | 실측: 프로세스 부모·명령줄 / 간섭 기전 미검증 | 변환 실패·타 작업 종료 위험 — F-5 COM 세션 설계 입력 | 🟠 |
| N15 | **`c5438a8` exe 기동 불가** — 빌드 환경 Python 3.14.7의 Tcl/Tk가 9.0.4(라이브러리 DLL 내장 zipfs)로 바뀐 뒤 PyInstaller 6.20.0이 `_tcl_data`·`_tk_data`를 번들하지 않는데 런타임 훅 `pyi_rth__tkinter`는 `_tcl_data`를 요구 → 시작 시 `FileNotFoundError`("Unhandled exception in script" 대화상자). E-1의 "5초 기동 smoke"는 프로세스 생존만 판정해 거짓 통과 | 실측(2026-09-27): exe 실행 대화상자 원문, git 이력 exe 6개 판독(`83103a7`~`c6e91df` Tcl 8.6·데이터 832/89개 → `c5438a8` Tcl 9.0·0/0개), `info library` = `//zipfs:/lib/tcl/tcl_library`, PyInstaller 훅에 zipfs 처리 없음 | 현 환경에서 빌드하는 모든 exe가 기동 불가, D-1(현 exe 릴리스) 실행 불가. 공개 v2026.08.06(Tcl 8.6)은 영향 없음 | 🔴 |
| N19 | 시행문 모드 빈 단락 — `build_doc`의 "두 번째 이후 depth 1 항목 앞 빈 줄" 규칙(`e402f41`, 2026-06-11)이 시행문 모드에서는 `가.` 단계(depth 1)에 걸려 `가.`↔`나.` 사이·`2.` 다음 `가.` 앞에 빈 단락이 생김(계획서 모드에서는 `1.` 절 사이 구분). 정본 §2-2 예시는 항목을 빈 줄 없이 연속 배치 — 의도 여부 확인 필요. main 동일 동작, 웨이브 2 회귀 아님 | 실측(2026-09-28): 실COM 산출물 단락 목록(파서 블록에는 빈 단락 없음)·1쪽 렌더 | 시행문 변환 뒤 빈 줄 수작업 삭제 | 🟡 |

### 11-4. 하류 호환 계약 (Track F 전 기간 불변)

| 표면 | 불변 조건 |
| :-- | :-- |
| CLI | 위치 인자 `files`, `-o/--output-dir`, `--insert-end-mark`(현행 의미 = 정규화 + 린트 + "끝") 유지 / 종료코드 0·1·2 의미 유지 |
| Python API | `main`·`convert_file`의 기존 인자 순서·기본값 유지, 신규 인자는 키워드·기본값으로만 추가 |
| 모듈 표면 | 실측 64개 참조 심볼의 `anyway_to_hwpx_com` import 경로 유지 — 이동 시 재노출 또는 해당 테스트 동시 갱신 |
| 산출물 | 이름 충돌 ` - N` 규칙 유지, 기본 동작에서 텍스트 자동 수정 없음(마스터 프롬프트 원칙) |

### 11-5. 트랙 상세

#### F-1 릴리스·저장소 정상화

- **목표**: 공개 최신 릴리스 = 검증된 `main` exe, 저장소는 소스만 추적
- **범위**: F-1a 현 `main` exe로 신규 릴리스 발행(재빌드 불요, D-1) / F-1b exe 추적 해제·배포는 Releases 전용(D-2) / F-1c 버전 표기(`__version__`·`--version`·GUI 창 제목, 다음 릴리스부터) / F-1d README 개발자 절에 릴리스 체크리스트 추가 / F-1e `dist/` 사용 안내·매뉴얼(05-28)의 현행 기능(PDF 두 모드·끝 표시·문서유형) 반영 여부 점검(갱신은 사용자 확인 후)·`handoff.md` 갱신·§10-3 skip 기록 정정(N14) / 로컬 `git gc`는 효과 실측 후 판단(UPX 바이너리는 델타 압축 효율 낮음)
- **비범위**: 이력 재작성(D-3), 코드 서명, 자동 업데이트
- **완료조건**
  - 최신 릴리스 태그가 가리키는 커밋에 E-7(`19806ca`)이 포함됨
  - 릴리스 노트에 exe SHA-256·크기·포함 수정(E-7)이 기록됨
  - `git ls-files dist` 결과가 비어 있음(D-2 승인 시)
  - `--version` 출력과 GUI 창 제목의 버전 문자열이 일치함(F-1c 적용 릴리스)
- **검증 센서**: 단위 스위트 → 샘플 변환 + `scripts/hwpx_editor_safety_gate.py` → exe 기동 smoke(사용자 실행 또는 명시 승인 하 실행 — "exe 세션 직접 사용 금지" 규칙 준수) → `gh release view`로 태그·자산 재조회
- **반복한도**: 빌드 2회, 동일 실패는 조건 변경 없이 재시도 금지
- **승인·검토**: F-1a·F-1b L4(사용자 명시 승인), F-1c·F-1d·F-1e L2 / 검토강도 enhanced(외부 공개 반영)

#### F-2 조용한 실패 제거 (관측성)

- **목표**: 변환 중 발생한 모든 경고가 CLI·GUI 동일 경로로 사용자에게 도달하고 결과 상태에 반영됨
- **범위**
  - F-2a 경고·참고 출력 10곳을 기존 note 수집 경로로 전환, 수집 종료 시점을 후처리 이후로 이동, CLI 중복 출력 제거
  - F-2b GUI: 경고 note 1건 이상인 파일을 `warning` 상태·로그 태그로 표시(기존 상태 체계 재사용)
  - F-2c 경량 자가검증(표준 라이브러리): ZIP 열림 · `mimetype` 첫 엔트리 STORED · 각 XML 파싱 · `header.xml`/`section0.xml` 루트 네임스페이스 · 표 `rowCnt`/`colCnt` 존재 — 실패 시 `[확인 필요]` note
  - F-2d `TableColWidth` 미지원을 1회 감지하면 같은 변환에서 재시도 중단, 문구는 `[참고]`로 강등(열 폭은 XML 후처리가 적용)
  - F-2e Markdown 이미지·링크 제거 시 건수 note(예: `[확인 필요] 이미지 2개 미삽입`)
  - F-2f E-6 흡수: Java 11 미만 note 한국어화 + 조치 안내(Java 11 이상 설치 또는 text 스택), README 요건 표 보강
- **비범위**: 후처리 단일 트랜잭션화(측정·필요 확인 전 보류), python-hwpx 게이트 내장, 경고 시 종료코드 변경(하류 계약), 로그 파일 저장
- **완료조건**
  - 후처리 6단계(여백·표·목록 내어쓰기·prid·줄 간격·단락 간격) 각각에 예외를 주입하면 `result['notes']`에 해당 경고가 1건 이상 포함됨
  - `anyway_to_hwpx_com.py`·`table_hwpx_postprocess.py`에서 note 수집을 거치지 않는 경고 `print`가 0곳임(grep)
  - 손상 HWPX 픽스처 3종(mimetype 순서 위반·XML 파손·`rowCnt` 누락)은 모두 자가검증 note 발생, 정상 샘플 산출물은 0건
  - GUI 상태 하네스의 `warning` 상태가 실제 note 경로로 재현됨
  - 실COM 샘플 변환 1회에서 `TableColWidth` 문구가 변환당 최대 1건
- **검증 센서**: 단위 스위트 · grep · `tests/gui_state_harness.py --state warning` · 실COM 샘플 변환 + HWP 열람(실물 검증)
- **반복한도·승인·검토**: 3회 / L2(로컬 수정)·L3(실COM 실행) / standard

#### F-3 옵션 정합성 (문서유형·공문 정규화 분리, 추가형)

- **목표**: 문서유형·공문 정규화·"끝" 표시를 독립적으로 선택 가능, 기존 호출의 산출 내용은 불변
- **범위**
  - F-3a `convert_file(..., doc_type='plan')` 키워드 인자 신설, 전역 `_ALLOW_ROMAN_LEVEL` 제거(`tests/test_roman_level_option.py` 동시 갱신)
  - F-3b `--official` 신설 = 날짜·금액 정규화 + 린트("끝" 없음). `--insert-end-mark`는 현행 그대로(정규화 포함)
  - F-3c GUI: 문서유형(계획·보고 / 시행문) 선택 + "공문 표기 정규화" 체크 추가, "끝 표시" 선택 시 정규화 자동 포함(현행 유지)
  - F-3d 시간 표기(§1-2) 린트 — 경고만, 자동 변환은 D-6
- **비범위**: 프로필 파일(JSON) 체계, 신규 문서유형 추가
- **완료조건**
  - `--insert-end-mark` 단독 변환의 blocks가 변경 전과 동일함(스냅샷 대조)
  - `--official` 단독 변환은 날짜·금액이 정규화되고 "끝" 블록이 없음
  - 한 프로세스에서 `sihaengmun` → `plan` 순으로 연속 변환하면 두 번째 결과에 로마숫자 레벨이 적용됨(전역 누수 없음)
  - `ConversionSnapshot`에 문서유형·정규화 필드가 있고 worker의 `convert_file` 호출까지 전달됨(단위 테스트)
  - 모놀리스의 `global` 선언이 0건(AST)
- **검증 센서**: 단위 스위트 · 스냅샷 대조 · GUI 상태 하네스 · 실COM `--doc-type sihaengmun` 변환 XML 들여쓰기 확인(§8 기록값 620 대조)
- **반복한도·승인·검토**: 3회 / L2 / standard + 하류 계약 영향으로 교차검토 권장

#### F-4 실물 회귀 체계 (골든 코퍼스)

- **목표**: 대표 문서 유형 전부를 실COM으로 변환·렌더링해 기준선 대비 변화를 한 번에 판정
- **범위**
  - F-4a 합성 골든 코퍼스 8종(`samples/golden/`, 공개 저장소이므로 합성·비식별만): ① 시행문(붙임·끝) ② 계획서(Ⅰ.·예산 표 금액·일정 표) ③ 보고서(병합 표·2쪽 이상 긴 표) ④ 양식(☐ 동의·서명란 2열 표) ⑤ CSV ⑥ XLSX 다중 시트 ⑦ DOCX(제목 스타일·표) ⑧ 텍스트 PDF(layout·editable)
  - F-4b `scripts/golden_run.py`: COM 세션 1개로 일괄 변환 → 자가검증(F-2c) → 안전 게이트 → HWP `SaveAs` PDF → 쪽수·표 수·콘텐츠 경계·경고 수·변환 시간 → `tests/out/golden/<날짜>/` 보고서 + 직전 기준선 diff
  - F-4c 첫 실행으로 기준선 확정(문서별 변환 시간·쪽수·경고 수) — 성능 과제는 이 수치로만 판단
  - F-4d F-1d 릴리스 체크리스트에 필수 단계로 편입
- **비범위**: CI 자동 실행(COM 필요), 픽셀 단위 시각 diff, 실제 업무 문서 투입
- **완료조건**
  - 8종 모두 변환 성공 · 자가검증 note 0건 · 게이트 PASS · PDF 재추출 성공
  - 긴 표 문서의 2쪽 상단 머리글 반복 여부가 보고서에 PASS/FAIL로 기록됨(FAIL이면 결함 등록)
  - 기준선 파일에 문서별 변환 시간·쪽수·경고 수가 기록됨
  - 재실행 시 차이가 없으면 "변화 없음", 있으면 항목별 diff가 출력됨
- **검증 센서**: 러너 보고서 + 기준선 확정 시 사용자 HWP 육안 검수 1회
- **반복한도·승인·검토**: 3회 / L3(실행 중 HWP 창 표시 — 실행 시점 사용자 고지) / standard

#### F-5 COM 세션 복구

- **목표**: 한 파일의 COM 실패가 같은 배치의 나머지 파일로 전파되지 않음
- **범위**: F-5a 파일 실패 시 경량 COM 호출로 인스턴스 상태 확인 → 이상이면 보호된 `Quit` 후 재생성, 배치당 재시작 최대 2회, 재시작 사실을 note로 기록(CLI `main`·GUI worker 공용 함수 1개) / F-5b CLI `finally`의 `hwp.Quit()` 예외 보호 / F-5c 고정 대기(시작 1.5s, 파일당 약 1.3s)는 F-4c 실측 후 단축 여부 판단(실측 없이 변경 금지)
- **비범위**: 병렬 변환, 프로세스 풀, 잔여 `Hwp.exe` 강제 종료
- **완료조건**
  - 가짜 HWP에 "2번째 파일에서 인스턴스 사망"을 주입하면 3번째 파일이 새 인스턴스로 성공하는 테스트 통과
  - 재시작 한도 초과 시 남은 파일이 사유와 함께 실패 목록에 기록됨
  - 실COM 골든 러너 결과가 F-4 기준선과 동일함(정상 경로 무회귀)
- **반복한도·승인·검토**: 3회 / L2·L3 / standard

#### F-6 Markdown 충실도 (결정 의존)

- **목표**: 원고의 그림·강조가 사용자가 선택한 방식대로 반영됨
- **범위**: F-6a 로컬 이미지 삽입(`![alt](경로)` → `InsertPicture`, 본문 폭 초과 시 비율 유지 축소, 원격 URL·없는 파일은 note) — D-4 / F-6b 굵게 보존 옵트인(`--keep-bold`), 기본은 현행(제거) — D-5
- **비범위**: 표 셀 안 이미지, 각주·하이퍼링크 필드, 원격 이미지 다운로드
- **완료조건**
  - 이미지 포함 샘플의 HWPX `BinData`에 이미지가 들어 있고 자가검증·게이트 PASS, HWP 열람 시 표시됨
  - `--keep-bold` 미지정 시 산출 텍스트·서식이 변경 전과 동일함
  - `--keep-bold` 지정 시 굵게 구간만 bold charPr run으로 분리됨(XML 확인)
- **반복한도·승인·검토**: 3회 / L2·L3 / standard

### 11-6. 실행 순서

| 웨이브 | 구성 | 선행 조건 | 세션(추정) |
| :-: | :-- | :-- | :-: |
| 1 | F-1a·F-1b(D-1·D-2 승인분)·F-1d·F-1e + F-2a·2b·2d·2e·2f | 없음 | 1 |
| 2 | F-2c + F-3 + F-1c(버전 표기, 다음 릴리스 준비) | 웨이브 1 | 1~2 |
| 3 | F-4 (기준선 확정) | F-2c(자가검증 재사용) | 1~2 |
| 4 | F-5 + F-6(D-4·D-5 결정분) | F-4 기준선 | 1~2 |

- 웨이브별 절차: `superpowers:writing-plans` 명세 → TDD(`superpowers:test-driven-development`) → 실COM 실물 검증 → 본 절에 결과 기록
- 역할 기본값: 실행 Codex / 검토 Claude(harness `_core/03`, 작업별 교체 허용)
- 서브모듈 주의: 본 저장소는 `~/.claude` 설정 저장소의 서브모듈(상위 포인터 `c5438a8`) — Track F 커밋마다 상위 포인터 변경이 발생하며, 상위 저장소 커밋·push는 별도 승인(CLAUDE.md §3 보호 대상)
- 공통 완료 게이트: 단위 스위트 green + `py_compile` + 웨이브 완료조건 전부 PASS + 실COM 실물 검증(HWP 열람·여백·글리프). 하나라도 미실시면 PARTIAL

### 11-7. 결정 대기

| ID | 결정 사항 | 권장안 | 근거 | 승인 |
| :-- | :-- | :-- | :-- | :-: |
| D-1 | 현 `main` exe로 신규 릴리스 발행 | 발행 — 노트에 E-7·SHA-256 기재 | N1 | L4 |
| D-2 | exe git 추적 해제 후 push | 해제 — 배포는 Releases 전용 | N10 | L4 |
| D-3 | 이력 재작성(exe 제거·force push) | 미실행 — 공개 저장소 클론·태그 영향 대비 효과 작음 | N10 | L5 |
| D-4 | Markdown 로컬 이미지 실제 삽입 | 도입 — 무통보 삭제 해소(알림은 F-2e로 선반영) | N7 | L2 |
| D-5 | 인라인 굵게 처리 | 옵트인 `--keep-bold`, 기본 현행(제거) — 공문 굵게 사용 드묾, AI 원고 과다 강조 | N7 | L2 |
| D-6 | 시간 표기 자동 변환 | 린트만 선도입(텍스트 자동 수정 금지 원칙), 실사용 후 재결정 | N9 | L2 |
| D-7 | 마스터 프롬프트 처리 | 공개 저장소 커밋 금지 / Vault 프롬프트 폴더 이동 또는 `.gitignore` 등록 중 선택(이동은 승인 필요) | N12 | L2 |
| D-8 | §10-3 "bs4 skip 방침" 미결 건 | 종결 — bs4 설치 확인, 현 skip 1건은 COM 게이트. 기록 정정만(F-1e) | N14 | — |
| D-9 | E-5 서식 프로필 추출 | 보류 유지 | §9·§10 | — |
| D-10 | COM 없는 직접 생성 백엔드(Mac·CI) | HOLD — md2hwpx 의도적 퇴역 결정 존중, Mac 경로는 kordoc(harness `_core/12`). 재개 조건: Mac 주력 전환 확정 시 스파이크부터 | 전략 | — |
| D-11 | N15 해소·릴리스 경로 | ① spec에서 빌드 시 Tcl/Tk 9 zipfs 라이브러리를 `_tcl_data`·`_tk_data`로 추출해 번들(신규 의존성 없음) → 재빌드 → 창 감지형 기동 확인 후 릴리스(권장) / ② PyInstaller 업그레이드(패키지 설치 승인·보안 심사 필요, 현 6.20.0 훅에 zipfs 처리 없어 효과 미확인) / ③ Tcl 8.6 Python 설치 후 빌드(프로그램 설치 승인 필요) / ④ 릴리스 보류(공개 v2026.08.06 유지, E-7 미해소) | N15 | L2(재빌드)·L4(발행) |

### 11-8. 리스크·완화

| 리스크 | 완화 |
| :-- | :-- |
| 정규화 분리로 하류 스킬 산출물 변화 | 11-4 계약 + `--insert-end-mark` blocks 스냅샷 대조 |
| 경고 가시화로 GUI `warning` 급증 | F-2d 예상 경고 강등 + 문구에 조치 안내 포함 |
| 실COM 비결정성(시작 실패·도중 오염) | F-5 복구 + 러너의 동일 실패 무조건 재시도 금지·조정 사항 기록 |
| 골든 코퍼스에 실무 문서 유입 | 합성·비식별만 사용, 커밋 전 개인정보·절대경로 grep |
| 모듈 표면 64개 결합으로 수정 파급 | 이동 대신 제자리 수정, 부득이한 이동은 재노출 |

- Track F 전체 비범위: 모놀리스 분해 단독 트랙, 후처리 트랜잭션화, COM 없는 백엔드(D-10), 신규 입력 형식, 코드 서명·자동 업데이트, E-5

### 11-9. 검증 명령 (저장소 루트)

```powershell
python -m unittest discover -s tests
python -m py_compile anyway_to_hwpx_com.py anyway_to_hwpx_gui.py
python anyway_to_hwpx_com.py --preflight
python anyway_to_hwpx_com.py samples\sample_complex.md -o tests\out\track-f --insert-end-mark
python scripts/hwpx_editor_safety_gate.py tests\out\track-f\sample_complex.hwpx
python tests/gui_state_harness.py --state warning --hold-seconds 0.2
python scripts/golden_run.py   # F-4 산출 예정
```

### 11-10. 웨이브 1 실행 결과 (2026-09-27, 브랜치 `feature/track-f-wave1`, 실행 Claude)

| 과제 | 판정 | 증거 |
| :-- | :-: | :-- |
| F-2a 경고 note 통합 | PASS | 경고 `print` 0곳(grep) · 후처리 6단계 실패가 `result['notes']`에 도달(단위 테스트) · CLI note 1회 출력(단위 테스트) |
| F-2b GUI 경고 반영 | PASS | `note_log_tag`·`finish_conversion` 단위 테스트 · GUI 상태 하네스 7개 상태 exit 0 |
| F-2d `TableColWidth` 1회 `[참고]` | PASS | 표 2개 → 조회 1회(단위 테스트) · 실COM 변환에서 `[참고]` 1회·`[경고]` 0건 |
| F-2e Markdown 이미지·링크 | PASS | `!alt` 잔류 결함 RED 재현 → 수정 · 실COM 산출물 본문에 alt·URL 부재 · note 각 1회 |
| F-2f Java 안내 한국어화(E-6) | PASS | 단위 테스트 2건(버전 확인·미확인 분기) · README 요구 사항 보강 |
| F-1b exe 추적 해제 | PASS | `main`에 `--no-ff` 병합(`d2b3343`) 후 push, `git ls-remote` 재조회 일치 · `git ls-files dist` 비어 있음 · 병합으로 작업 트리에서 빠진 로컬 exe는 `c5438a8` blob에서 덮어쓰기 금지 방식으로 복원(SHA-256 일치, ignored) |
| F-1d 릴리스 절차 | PASS | README.ko.md·README.md 개발자 절 |
| F-1e 문서 점검·정정 | PASS / 갱신 보류 | §10-3 정정(N14) · `dist/` 안내 문서(05-28, txt·html·pdf 5종)는 PDF 두 모드·드래그 앤 드롭·저장 폴더 비우기·경고 대화상자 미반영 — 갱신은 사용자 확인 후 |
| D-11 ① 시험 작업(브랜치 `spike/tcl9-bundle`) | PASS | spec이 Tcl/Tk 라이브러리가 zipfs일 때만 빌드 workpath로 복사해 `_tcl_data`·`_tk_data` 번들(Tcl 8.6이면 무동작) → 격리 빌드 `C:\tmp\hwpx-gui-tcl9-spike`(75,106,019 bytes, SHA-256 `53ebe0775ab0e6b005b7fc274f9dda0355779ebda8b488405af0d2d71809b528`) → 번들 839·90개(`init.tcl`·`tk.tcl`·`encoding` 83개) → 창 감지형 기동 2회 PASS(메인 창 12.4s·25.6s, 오류 대화상자 없음, `WM_CLOSE` exit 0) + 5초 유지 1회 PASS → 내장 코드에 E-7·웨이브 1 반영 확인. 채택(`main` 병합)·발행은 별도 확인 |
| 동결 exe GUI 변환(채택 후, `ccd76bd` 빌드 입력) | PASS / 한글 재열람 보류 | 화면 조작으로 `wave1_check.md` 변환 → 로그 태그(`[확인 필요]` 빨강·`[참고]` 회색)·상태 "변환 완료 1개 · 확인 필요 1개"·대화상자 "변환 완료(확인 필요)" 확인(F-2b 동결 앱 종단 확인) → 산출물 구조 검증 7/7(안전 게이트 포함). 저장 경로 `C:\tmp\…`에서 한글 파일 접근 확인 창 발생 → 1회 "접근 허용"(N16). 저장본 한글 재열람은 다른 문서가 한글에서 사용 중이라 보류 |
| F-1a 릴리스(재개) | PASS | `main` 6커밋 push(`768e275`, `ls-remote` 일치) → `v2026.09.27` 발행(태그 → `768e275`, E-7 `19806ca` 포함, Latest) → API 자산 digest `sha256:53ebe0775ab0e6b005b7fc274f9dda0355779ebda8b488405af0d2d71809b528` = 로컬 SHA-256, 75,106,019 bytes. 저장본 한글 재열람은 사용자 확인(진행 지시 메시지 기준) |
| F-1a 릴리스(최초 시도) | BLOCKED → 해소 | 디스크 exe blob = `c5438a8` blob(`2a61e81`) · 73,746,447 bytes · SHA-256 `9369b286f1ed9bf23fe57c1f994181522ce151068820c57f6e8888554e818824` · 내장 `anyway_to_hwpx_com.pyc`에 E-7(`HSecDef`) 포함 판독 — 그러나 사용자 승인 후 실행한 창 감지형 기동 확인에서 60초 내 메인 창 미출현·"Unhandled exception in script" 대화상자(N15) → 발행 중단, 재개 조건 D-11 |

- 공통 게이트: 단위 스위트 258 tests OK(skip 1 = COM 게이트) · `py_compile` · 실COM 변환 exit 0 · 안전 게이트 PASS · 한글 재열람·PDF 저장·1쪽 렌더 육안 확인 포함 실물 검증 11/11 PASS
- NOT_RUN: 실COM PDF layout 통합 테스트(약 26분) — layout 경로 변경은 note 합류 1줄이며 단위 테스트(layout 경로 6건)로 확인
- 계획 대비 조정: F-2 완료조건 "GUI 상태 하네스 `warning`이 실제 note 경로로 재현"은 모달 대화상자 때문에 `finish_conversion` 단위 테스트(대화상자 패치)로 대체 검증
- 관찰(범위 밖, 후속 후보)
  - 줄 간격 후처리는 paraPr 직계 `lineSpacing`만 갱신 — 본문 참조 paraPr은 switch 내부까지 160%(실측)라 영향 없음. 미사용 기본 스타일(머리말 150·각주 130 등)은 직계/switch 값 불일치 잔존
  - 표 뒤 빈 단락 3개 연속(표 뒤 빈 줄 + 1단계 항목 앞 빈 줄 + 표 종료 줄바꿈) — 정본 §8-1 "표 앞뒤 단락 구분" 대비 과다 여부 검토 후보

### 11-11. 웨이브 2 실행 결과 (2026-09-28, 브랜치 `feature/track-f-wave2`, 실행 Claude)

| 과제 | 판정 | 증거 |
| :-- | :-: | :-- |
| F-1c 버전 표기 | PASS | `__version__='2026.09.27+dev'`, `--version`(저장소 CLI·전역 shim 동일), GUI 제목, README 릴리스 절차 1단계 |
| F-3a 문서유형 ContextVar | PASS | `detect_and_parse(doc_type=…)` 범위 설정·복원, 연속 변환 무누수·알 수 없는 유형 거부·`global` 0건 테스트 |
| F-3b `--official` | PASS | 특성화(`--insert-end-mark` 현행 고정)·정규화만 적용·CLI 전달 테스트. 작성 중 N17 발견 |
| F-3d 시간 린트 + 표기 점검 등급 | PASS | 사용자 결정으로 표기 린트 4종 `[표기 점검]`(로그 파랑, '확인 필요' 집계 제외), 샘플 오탐 0 |
| F-3c GUI 선택 | PASS | 문서 유형·정규화 컨트롤, 스냅샷→worker 전달 테스트, PrintWindow 캡처 700×560·700×600·800×680 → `minsize` 560→600 |
| F-2c 자가검증 | PASS(단위) | 손상 픽스처 5종 검출·정상 0건, 웨이브 1 실COM 산출물 0건 |
| 실COM 검증(Task 7) 1차 | BLOCKED | 첫 변환이 한글 파일 접근 확인 창에서 대기(N16-보강) 중 다른 자동화 클라이언트의 한글 사용 확인(N18) → 반복 작업 중지, 다른 창 미조작. 재개 조건: 한글 미사용 확인 + N16 처리 결정 |
| N16 등록 이름 프로브 | 원인 확인 | 사용자 결정(프로브→수정→검증). 한글 미실행 확인 후 파일 미개봉 프로브: `RegisterModule('FilePathCheckDLL', 'SecurityModule')` = **False**, 레지스트리 등록명 `'FilePathCheckerModule'` = **True** → 기존 코드의 등록은 줄곧 실패, 확인 창의 직접 원인 |
| N16 수정 | PASS | `45ffb38` — HKCU 등록 이름(읽기 전용) 먼저, 관례 이름 `SecurityModule`은 마지막 시도 / 모두 실패 시 `[확인 필요]` 경고(CLI stderr·GUI 로그 err·`--preflight` 실패). 테스트: 등록 이름 우선·실패 경고·GUI 로그 배선(배선 제거 시 RED 확인) |
| N17 수정 | PASS | `d230db5` — 끝 온점 앞 공백은 온점이 있을 때만 소비. 실COM 산출물 `2026. 3. 22. 행사` 확인 |
| 실COM 검증(Task 7) 재개 | PASS | 워크트리 코드(`converter: C:\tmp\hwpx-wave2\…`, `2026.09.27+dev`), 실행 폴더 `tests/out/track-f/w2/run-20260928-080626/`. 3건(레이아웃 PDF·`--doc-type sihaengmun`·`--official`) 모두 exit 0·보안 모듈 경고 0·확인 창 0·자가검증 note 0·편집기 안전 게이트 PASS. 시행문 `1.` `hc:left` 620·`가.` 960(§8 기록값 일치). `--official`: `2026. 3. 22. 행사`·`금400,000원(금사십만원)`·'끝' 없음·시간 린트 1건(`오후 3시 20분` → `15:20`). 한글 재열람→PDF 1쪽 렌더 2건 육안 확인. 실행 전후 `Hwp.exe` 0개, 외부 한글 병행 0건. 발견: N19 |

- 단위 스위트 292 tests OK(skip 1, N16·N17 테스트 포함 — 1차 기록 284), `py_compile` 43개 OK, AST `global` 0건, GUI 하네스 7개 상태 exit 0 (2026-09-28, `45ffb38`)
- 실COM 안전장치(`run_task7.py`, 저장소 밖): 단계마다 시작 전 `Hwp.exe` 잔존 시 중단, 단계 중 `Hwp.exe` 2개 이상이면 외부 한글로 보고 중단, 90초 초과·보안 모듈 경고 즉시 중단, 중단 시 자기 하위 파이썬만 종료(한글 프로세스·창 미조작), 재실행 오판 방지용 실행별 새 폴더
