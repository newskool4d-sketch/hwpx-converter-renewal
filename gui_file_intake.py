"""Pure file-picker and file-drop input normalization."""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from enum import StrEnum
from os import PathLike, fspath
from pathlib import Path
from typing import TypeAlias


InputPath: TypeAlias = str | PathLike[str]


@dataclass(frozen=True, slots=True)
class RawTkDndEventDataError(TypeError):
    """Raised when raw Tcl event data bypasses the caller's splitlist boundary."""

    raw_event_data: str

    def __str__(self) -> str:
        return "raw TkDND event data is not a split path sequence"


class RejectionReason(StrEnum):
    """Reasons a dropped or selected path cannot be converted."""

    MISSING = "missing"
    NOT_A_FILE = "not_a_file"
    UNSUPPORTED_EXTENSION = "unsupported_extension"


@dataclass(frozen=True, slots=True)
class RejectedInputPath:
    """A rejected input together with its machine-readable reason."""

    path: Path
    reason: RejectionReason


@dataclass(frozen=True, slots=True)
class NormalizedInputPaths:
    """Immutable candidate classification shared by picker and file drops."""

    accepted: tuple[Path, ...]
    duplicates: tuple[Path, ...]
    rejected: tuple[RejectedInputPath, ...]
    busy: tuple[Path, ...] = ()


def normalize_input_paths(
    input_paths: Sequence[InputPath],
    supported_extensions: Collection[str],
) -> NormalizedInputPaths:
    """Normalize supported regular files and classify duplicate or rejected paths."""
    allowed_extensions = frozenset(extension.casefold() for extension in supported_extensions)
    accepted: list[Path] = []
    duplicates: list[Path] = []
    rejected: list[RejectedInputPath] = []
    known_paths: set[Path] = set()

    for input_path in input_paths:
        path = Path(fspath(input_path)).expanduser().resolve(strict=False)
        if not path.exists():
            rejected.append(RejectedInputPath(path, RejectionReason.MISSING))
            continue
        if not path.is_file():
            rejected.append(RejectedInputPath(path, RejectionReason.NOT_A_FILE))
            continue
        if path.suffix.casefold() not in allowed_extensions:
            rejected.append(RejectedInputPath(path, RejectionReason.UNSUPPORTED_EXTENSION))
            continue
        if path in known_paths:
            duplicates.append(path)
            continue
        known_paths.add(path)
        accepted.append(path)

    return NormalizedInputPaths(
        accepted=tuple(accepted),
        duplicates=tuple(duplicates),
        rejected=tuple(rejected),
    )


@dataclass(frozen=True, slots=True)
class AddedInputPaths:
    """Immutable selection update and output-folder decision."""

    accepted: tuple[Path, ...]
    duplicates: tuple[Path, ...]
    rejected: tuple[RejectedInputPath, ...]
    busy: tuple[Path, ...]
    selection: tuple[Path, ...]
    output_directory: Path | None


def add_input_paths(
    input_paths: Sequence[InputPath],
    existing_selection: Sequence[InputPath],
    supported_extensions: Collection[str],
    *,
    is_busy: bool,
    output_directory: InputPath | None,
) -> AddedInputPaths:
    """Add valid paths without mutating caller state or accepting while busy."""
    selection = _deduplicated_canonical_paths(existing_selection)
    configured_output_directory = _configured_output_directory(output_directory)

    if is_busy:
        return AddedInputPaths(
            accepted=(),
            duplicates=(),
            rejected=(),
            busy=tuple(_canonical_path(input_path) for input_path in input_paths),
            selection=selection,
            output_directory=configured_output_directory,
        )

    normalized = normalize_input_paths(input_paths, supported_extensions)
    known_paths = set(selection)
    accepted_candidates = set(normalized.accepted)
    accepted: list[Path] = []
    duplicates: list[Path] = []

    for input_path in input_paths:
        path = _canonical_path(input_path)
        if path not in accepted_candidates:
            continue
        if path in known_paths:
            duplicates.append(path)
            continue
        known_paths.add(path)
        accepted.append(path)

    accepted_paths = tuple(accepted)
    default_output_directory = (
        configured_output_directory
        if configured_output_directory is not None
        else accepted_paths[0].parent if accepted_paths else None
    )
    return AddedInputPaths(
        accepted=accepted_paths,
        duplicates=tuple(duplicates),
        rejected=normalized.rejected,
        busy=(),
        selection=selection + accepted_paths,
        output_directory=default_output_directory,
    )


def input_paths_from_tkdnd_splitlist(split_paths: Sequence[str]) -> tuple[str, ...]:
    """Accept only the result of a caller-owned `tk.splitlist(event.data)` call."""
    if isinstance(split_paths, str):
        raise RawTkDndEventDataError(raw_event_data=split_paths)
    return tuple(split_paths)


def _deduplicated_canonical_paths(input_paths: Sequence[InputPath]) -> tuple[Path, ...]:
    known_paths: set[Path] = set()
    paths: list[Path] = []
    for input_path in input_paths:
        path = _canonical_path(input_path)
        if path not in known_paths:
            known_paths.add(path)
            paths.append(path)
    return tuple(paths)


def _configured_output_directory(output_directory: InputPath | None) -> Path | None:
    if output_directory is None:
        return None
    configured_path = fspath(output_directory).strip()
    if not configured_path:
        return None
    return _canonical_path(configured_path)


def _canonical_path(input_path: InputPath) -> Path:
    return Path(fspath(input_path)).expanduser().resolve(strict=False)
