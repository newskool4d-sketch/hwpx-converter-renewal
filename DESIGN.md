# HWPX 변환기 UI 계약

이 문서는 Tkinter 화면을 위한 IBM Carbon 계열의 최소 디자인 계약이다. IBM 로고나 마케팅 자산을 사용하지 않는다.

## 기본 원칙

- 4px grid를 사용한다. 기본 화면은 밝은 표면과 짙은 텍스트를 우선한다.
- 카드, 입력란, 버튼, 컨테이너의 모서리는 `0px`이다. 작은 상태 표식에만 `2px`를 허용한다.
- 카드와 구획은 `1px` hairline 및 표면 차이로 구분한다. shadow, gradient, pill 형태를 사용하지 않는다.
- 포커스는 `2px` IBM Blue outline으로 표시한다.
- 글꼴은 `IBM Plex Sans`, `맑은 고딕`, `Arial`, `sans-serif` 순으로 대체한다. 본문은 보통 굵기, 제목은 필요한 경우에만 강조한다.

## 공개 Tkinter 토큰

`ui_design.py`는 다음 불변 토큰을 제공한다.

| 토큰 | 값 | 용도 |
| --- | --- | --- |
| `ACTION_BLUE` | `#0F62FE` | action, focus, info, valid drop |
| `SUCCESS_GREEN` | `#24A148` | success |
| `WARNING_YELLOW` | `#F1C21B` | warning, partial drop |
| `ERROR_RED` | `#DA1E28` | error, rejected drop |
| `UI_GEOMETRY["corner_radius_px"]` | `0` | 평면 사각형 모서리 |
| `UI_GEOMETRY["focus_outline_px"]` | `2` | focus outline |

## 상태 색 사용 규칙

유채색은 상태 신호에만 사용한다. `UI_STATE_COLORS`의 전체 허용 매핑은 아래와 같다.

| 상태 | 색 |
| --- | --- |
| `action`, `focus`, `info`, `drop-valid` | `ACTION_BLUE` |
| `success` | `SUCCESS_GREEN` |
| `warning`, `drop-partial` | `WARNING_YELLOW` |
| `error`, `drop-rejected` | `ERROR_RED` |

Green, Yellow, Red는 장식, 일반 버튼, 카드 표면, 일반 강조색으로 사용할 수 없다. Blue도 action/focus/info/valid-drop 상태 외의 장식에는 사용하지 않는다. 일반 버튼은 중립 표면 또는 `ACTION_BLUE`의 action 의미가 있는 primary action만 사용한다.

상태 토큰은 읽기 전용이다. 상태를 갱신할 때는 복사본을 변경하지 말고 현재 상태 이름으로 `UI_STATE_COLORS`를 조회한다.
