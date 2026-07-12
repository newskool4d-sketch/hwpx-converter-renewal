from __future__ import annotations

from typing import Final

import ui_design


SUPPORTED_PATTERNS: Final = [
    ("Supported files", "*.md *.txt *.docx *.html *.htm *.csv *.xlsx *.pdf"),
    ("Markdown", "*.md"),
    ("Text", "*.txt"),
    ("Word", "*.docx"),
    ("HTML", "*.html *.htm"),
    ("Spreadsheet", "*.csv *.xlsx"),
    ("PDF", "*.pdf"),
    ("All files", "*.*"),
]
SUPPORTED_EXTENSIONS: Final = (".md", ".txt", ".docx", ".html", ".htm", ".csv", ".xlsx", ".pdf")
BG: Final = "white"
CARD: Final = "white"
BORDER: Final = "gray80"
ACCENT: Final = ui_design.UI_STATE_COLORS["action"]
ACCENT_DARK: Final = ui_design.UI_STATE_COLORS["focus"]
ACCENT_DIM: Final = "gray65"
TEXT: Final = "black"
MUTED: Final = "gray35"
GREEN: Final = ui_design.UI_STATE_COLORS["success"]
YELLOW: Final = ui_design.UI_STATE_COLORS["warning"]
RED: Final = ui_design.UI_STATE_COLORS["error"]
TROUGH: Final = "gray85"
LOG_BG: Final = "gray95"
FONT: Final = (ui_design.UI_FONT_FAMILY[0], 10)
FONT_BOLD: Final = (ui_design.UI_FONT_FAMILY[0], 10, "bold")
FONT_SMALL: Final = (ui_design.UI_FONT_FAMILY[0], 9)
FONT_TITLE: Final = (ui_design.UI_FONT_FAMILY[0], 15, "bold")
EDITABLE_FORMATTING_NOTICE: Final = (
    "편집: 줄간격 160% · 아래 2 · 장평/자간 기본 · 어절 보호"
)
