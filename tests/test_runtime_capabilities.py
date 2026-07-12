from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from runtime_capabilities import (
    CapabilityMode,
    capability_from_modules,
    detect_capabilities,
    probe_java_major,
)


class RuntimeCapabilitiesTests(unittest.TestCase):
    def test_full_stack_requires_layout_odl_and_java_11(self) -> None:
        capability = capability_from_modules(
            {
                "fitz": True,
                "pdfplumber": True,
                "pypdf": True,
                "opendataloader": True,
                "tkinterdnd2": True,
            },
            java_major=17,
        )

        self.assertEqual(capability.mode, CapabilityMode.FULL)
        self.assertTrue(capability.layout_enabled)
        self.assertTrue(capability.editable_enabled)
        self.assertTrue(capability.odl_enabled)
        self.assertTrue(capability.pdf_enabled)
        self.assertTrue(capability.dnd_enabled)
        self.assertIn(".pdf", capability.effective_gui_extensions)

    def test_text_fallback_keeps_layout_when_java_is_old(self) -> None:
        capability = capability_from_modules(
            {"fitz": True, "pdfplumber": True, "pypdf": True, "opendataloader": True},
            java_major=8,
        )

        self.assertEqual(capability.mode, CapabilityMode.TEXT)
        self.assertTrue(capability.layout_enabled)
        self.assertTrue(capability.editable_enabled)
        self.assertFalse(capability.odl_enabled)
        self.assertFalse(capability.pdf_disabled)
        self.assertIn(".pdf", capability.effective_input_extensions)

    def test_none_stack_disables_pdf_input_and_removes_extension(self) -> None:
        capability = capability_from_modules(
            {"fitz": False, "pdfplumber": False, "pypdf": False, "opendataloader": False},
            java_major=None,
        )

        self.assertEqual(capability.mode, CapabilityMode.NONE)
        self.assertFalse(capability.layout_enabled)
        self.assertFalse(capability.editable_enabled)
        self.assertFalse(capability.odl_enabled)
        self.assertFalse(capability.pdf_enabled)
        self.assertTrue(capability.pdf_disabled)
        self.assertNotIn(".pdf", capability.effective_gui_extensions)
        self.assertNotIn(".pdf", capability.effective_input_extensions)

    def test_malformed_module_values_cannot_enable_a_stack(self) -> None:
        capability = capability_from_modules(
            {"fitz": 1, "pdfplumber": "yes", "pypdf": [], "opendataloader": object()},
            java_major=99,
        )

        self.assertEqual(capability.mode, CapabilityMode.NONE)
        self.assertFalse(capability.pdf_enabled)

    def test_detect_uses_find_spec_and_java_probe_without_global_mode(self) -> None:
        module_names: list[str] = []

        def finder(name: str) -> object | None:
            module_names.append(name)
            return object() if name in {"fitz", "pdfplumber", "pypdf"} else None

        capability = detect_capabilities(module_finder=finder, java_probe=lambda: 8)

        self.assertEqual(capability.mode, CapabilityMode.TEXT)
        self.assertIn("fitz", module_names)
        self.assertIn("opendataloader_pdf", module_names)
        self.assertFalse(capability.odl_enabled)

    def test_java_probe_parses_major_and_bounds_timeout(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["java", "-version"],
            returncode=0,
            stdout="",
            stderr='openjdk version "17.0.12" 2024-07-16\n',
        )

        with patch("runtime_capabilities.subprocess.run", return_value=completed) as run:
            self.assertEqual(probe_java_major(), 17)

        self.assertEqual(run.call_args.kwargs["timeout"], 5.0)

    def test_java_probe_handles_missing_and_malformed_output(self) -> None:
        with patch(
            "runtime_capabilities.subprocess.run",
            side_effect=FileNotFoundError("java"),
        ):
            self.assertIsNone(probe_java_major())

        malformed = subprocess.CompletedProcess(
            args=["java", "-version"], returncode=0, stdout="", stderr="not java output"
        )
        with patch("runtime_capabilities.subprocess.run", return_value=malformed):
            self.assertIsNone(probe_java_major())


if __name__ == "__main__":
    unittest.main()
