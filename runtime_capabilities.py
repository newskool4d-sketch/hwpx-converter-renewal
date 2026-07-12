from __future__ import annotations

import importlib.util
import re
import subprocess
from dataclasses import dataclass
from enum import Enum
from importlib.machinery import ModuleSpec
from typing import Final, Mapping, Protocol


class CapabilityMode(str, Enum):
    FULL = "full"
    TEXT = "text"
    NONE = "none"


DEFAULT_INPUT_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {".md", ".txt", ".docx", ".html", ".htm", ".csv", ".xlsx", ".pdf"}
)
JAVA_PROBE_TIMEOUT_SECONDS: Final[float] = 5.0
_JAVA_VERSION_PATTERN: Final[re.Pattern[str]] = re.compile(
    r'version\s+"(?P<version>\d+(?:\.\d+)*)"', re.IGNORECASE
)
_MODULE_NAMES: Final[tuple[str, ...]] = (
    "fitz",
    "pdfplumber",
    "pypdf",
    "opendataloader_pdf",
    "tkinterdnd2",
)


class ModuleFinder(Protocol):
    def __call__(self, name: str) -> ModuleSpec | None: ...


class JavaProbe(Protocol):
    def __call__(self) -> int | None: ...


@dataclass(frozen=True, slots=True)
class RuntimeCapabilities:
    mode: CapabilityMode
    layout_enabled: bool
    editable_enabled: bool
    odl_enabled: bool
    pdf_enabled: bool
    dnd_enabled: bool
    effective_input_extensions: frozenset[str]
    java_major: int | None
    available_modules: frozenset[str]

    @property
    def effective_gui_extensions(self) -> frozenset[str]:
        return self.effective_input_extensions

    @property
    def supports_layout(self) -> bool:
        return self.layout_enabled

    @property
    def supports_editable(self) -> bool:
        return self.editable_enabled

    @property
    def supports_pdf(self) -> bool:
        return self.pdf_enabled

    @property
    def pdf_disabled(self) -> bool:
        return not self.pdf_enabled

    @property
    def editable_fallback_enabled(self) -> bool:
        return self.editable_enabled and not self.odl_enabled

    def __str__(self) -> str:
        return (
            f"mode={self.mode.value} layout_enabled={self.layout_enabled} "
            f"editable_enabled={self.editable_enabled} odl_enabled={self.odl_enabled} "
            f"editable_fallback_enabled={self.editable_fallback_enabled} "
            f"pdf_disabled={self.pdf_disabled} dnd_enabled={self.dnd_enabled}"
        )


def _is_true(value: bool | None) -> bool:
    return value is True


def _normalise_java_major(value: int | None) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None


def capability_from_modules(
    modules: Mapping[str, bool],
    *,
    java_major: int | None = None,
) -> RuntimeCapabilities:
    fitz_available = _is_true(modules.get("fitz"))
    fallback_available = any(
        _is_true(modules.get(name)) for name in ("fitz", "pdfplumber", "pypdf")
    )
    odl_available = any(
        _is_true(modules.get(name))
        for name in ("opendataloader_pdf", "opendataloader", "opendataloader-pdf")
    )
    detected_java = _normalise_java_major(java_major)
    odl_enabled = odl_available and detected_java is not None and detected_java >= 11
    layout_enabled = fitz_available
    editable_enabled = fallback_available or odl_enabled
    mode = (
        CapabilityMode.FULL
        if layout_enabled and odl_enabled
        else CapabilityMode.TEXT
        if layout_enabled and editable_enabled
        else CapabilityMode.NONE
    )
    pdf_enabled = mode is not CapabilityMode.NONE
    extensions = DEFAULT_INPUT_EXTENSIONS if pdf_enabled else DEFAULT_INPUT_EXTENSIONS - {".pdf"}
    available_modules = frozenset(
        name for name in _MODULE_NAMES if _is_true(modules.get(name))
    )
    return RuntimeCapabilities(
        mode=mode,
        layout_enabled=layout_enabled,
        editable_enabled=editable_enabled,
        odl_enabled=odl_enabled,
        pdf_enabled=pdf_enabled,
        dnd_enabled=_is_true(modules.get("tkinterdnd2")),
        effective_input_extensions=frozenset(extensions),
        java_major=detected_java,
        available_modules=available_modules,
    )


def detect_capabilities(
    *,
    module_finder: ModuleFinder | None = None,
    java_probe: JavaProbe | None = None,
) -> RuntimeCapabilities:
    finder = module_finder or importlib.util.find_spec
    modules: dict[str, bool] = {}
    for name in _MODULE_NAMES:
        try:
            modules[name] = finder(name) is not None
        except (ImportError, ValueError, AttributeError):
            modules[name] = False
    probe = java_probe or probe_java_major
    return capability_from_modules(modules, java_major=probe())


def probe_java_major(timeout_seconds: float = JAVA_PROBE_TIMEOUT_SECONDS) -> int | None:
    try:
        result = subprocess.run(
            ["java", "-version"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (FileNotFoundError, PermissionError, subprocess.SubprocessError, OSError):
        return None
    output = f"{result.stdout or ''}\n{result.stderr or ''}"
    match = _JAVA_VERSION_PATTERN.search(output)
    if match is None:
        return None
    version = match.group("version").split(".")
    major_text = version[1] if version[0] == "1" and len(version) > 1 else version[0]
    try:
        return int(major_text)
    except ValueError:
        return None


__all__ = [
    "CapabilityMode",
    "DEFAULT_INPUT_EXTENSIONS",
    "JAVA_PROBE_TIMEOUT_SECONDS",
    "RuntimeCapabilities",
    "capability_from_modules",
    "detect_capabilities",
    "probe_java_major",
]
