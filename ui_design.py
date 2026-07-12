from collections.abc import Mapping
from types import MappingProxyType
from typing import Final


ACTION_BLUE: Final[str] = "#0F62FE"
SUCCESS_GREEN: Final[str] = "#24A148"
WARNING_YELLOW: Final[str] = "#F1C21B"
ERROR_RED: Final[str] = "#DA1E28"
UI_FONT_FAMILY: Final[tuple[str, ...]] = (
    "IBM Plex Sans",
    "맑은 고딕",
    "Arial",
    "sans-serif",
)
UI_GEOMETRY: Final[Mapping[str, int]] = MappingProxyType(
    {"corner_radius_px": 0, "focus_outline_px": 2}
)
UI_STATE_COLORS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "action": ACTION_BLUE,
        "focus": ACTION_BLUE,
        "info": ACTION_BLUE,
        "drop-valid": ACTION_BLUE,
        "success": SUCCESS_GREEN,
        "warning": WARNING_YELLOW,
        "drop-partial": WARNING_YELLOW,
        "error": ERROR_RED,
        "drop-rejected": ERROR_RED,
    }
)
