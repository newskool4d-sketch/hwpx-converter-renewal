import unittest


class UiDesignContractTests(unittest.TestCase):
    def test_semantic_colors_match_carbon_contract(self) -> None:
        import ui_design

        self.assertEqual(ui_design.ACTION_BLUE, "#0F62FE")
        self.assertEqual(ui_design.SUCCESS_GREEN, "#24A148")
        self.assertEqual(ui_design.WARNING_YELLOW, "#F1C21B")
        self.assertEqual(ui_design.ERROR_RED, "#DA1E28")

    def test_font_fallback_and_flat_geometry_are_public_contracts(self) -> None:
        import ui_design

        self.assertEqual(
            ui_design.UI_FONT_FAMILY,
            ("IBM Plex Sans", "맑은 고딕", "Arial", "sans-serif"),
        )
        self.assertEqual(ui_design.UI_GEOMETRY["corner_radius_px"], 0)
        self.assertEqual(ui_design.UI_GEOMETRY["focus_outline_px"], 2)

    def test_editable_formatting_notice_fits_the_minimum_window(self) -> None:
        from gui_theme import EDITABLE_FORMATTING_NOTICE

        self.assertLessEqual(len(EDITABLE_FORMATTING_NOTICE), 40)
        for required_text in ("160%", "아래 2", "장평/자간", "어절 보호"):
            self.assertIn(required_text, EDITABLE_FORMATTING_NOTICE)

    def test_state_colors_are_complete_immutable_and_semantic_only(self) -> None:
        import ui_design

        expected = {
            "action": ui_design.ACTION_BLUE,
            "focus": ui_design.ACTION_BLUE,
            "info": ui_design.ACTION_BLUE,
            "drop-valid": ui_design.ACTION_BLUE,
            "success": ui_design.SUCCESS_GREEN,
            "warning": ui_design.WARNING_YELLOW,
            "drop-partial": ui_design.WARNING_YELLOW,
            "error": ui_design.ERROR_RED,
            "drop-rejected": ui_design.ERROR_RED,
        }
        self.assertEqual(dict(ui_design.UI_STATE_COLORS), expected)

        color_families = {
            ui_design.ACTION_BLUE: {"action", "focus", "info", "drop-valid"},
            ui_design.SUCCESS_GREEN: {"success"},
            ui_design.WARNING_YELLOW: {"warning", "drop-partial"},
            ui_design.ERROR_RED: {"error", "drop-rejected"},
        }
        for color, states in color_families.items():
            self.assertEqual(
                {state for state, mapped_color in ui_design.UI_STATE_COLORS.items() if mapped_color == color},
                states,
            )

        with self.assertRaises(TypeError):
            ui_design.UI_STATE_COLORS["action"] = ui_design.ERROR_RED

        stale_copy = dict(ui_design.UI_STATE_COLORS)
        stale_copy["action"] = ui_design.ERROR_RED
        self.assertEqual(ui_design.UI_STATE_COLORS["action"], ui_design.ACTION_BLUE)


if __name__ == "__main__":
    unittest.main()
