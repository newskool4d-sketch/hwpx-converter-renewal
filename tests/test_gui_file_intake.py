from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from gui_file_intake import (
    RejectionReason,
    add_input_paths,
    input_paths_from_tkdnd_splitlist,
    normalize_input_paths,
)


SUPPORTED_EXTENSIONS = (
    ".md",
    ".txt",
    ".docx",
    ".html",
    ".htm",
    ".csv",
    ".xlsx",
    ".pdf",
)


class TestNormalizeInputPaths(unittest.TestCase):
    def test_preserves_existing_picker_order_for_supported_regular_files(self) -> None:
        # Given: supported regular files in the converter's picker order.
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            first = directory / "first source.md"
            second = directory / "second source.pdf"
            first.write_text("# first", encoding="utf-8")
            second.write_bytes(b"%PDF")

            # When: the shared pure picker/drop normalizer receives them.
            result = normalize_input_paths(
                (str(first), str(second)),
                SUPPORTED_EXTENSIONS,
            )

            # Then: accepted paths are canonical and retain source order.
            self.assertEqual(result.accepted, (first.resolve(), second.resolve()))

    def test_classifies_duplicate_missing_directory_and_unsupported_paths(self) -> None:
        # Given: one valid spaced PDF, its duplicate, and three invalid input kinds.
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory) / "drop folder"
            directory.mkdir()
            valid = directory / "valid file.PDF"
            valid.write_bytes(b"%PDF")
            missing = directory / "missing file.pdf"
            unsupported = directory / "notes.rtf"
            unsupported.write_text("unsupported", encoding="utf-8")

            # When: candidates include all supported picker/drop failure categories.
            result = normalize_input_paths(
                (str(valid), str(valid), str(missing), str(directory), str(unsupported)),
                SUPPORTED_EXTENSIONS,
            )

            # Then: regular files, canonical duplicates, and rejection reasons are separated.
            self.assertEqual(result.accepted, (valid.resolve(),))
            self.assertEqual(result.duplicates, (valid.resolve(),))
            self.assertEqual(
                tuple(item.reason for item in result.rejected),
                (
                    RejectionReason.MISSING,
                    RejectionReason.NOT_A_FILE,
                    RejectionReason.UNSUPPORTED_EXTENSION,
                ),
            )


class TestAddInputPaths(unittest.TestCase):
    def test_adds_new_paths_without_mutating_caller_state_and_defaults_output_directory(self) -> None:
        # Given: an empty selection, a blank output folder, and one spaced PDF path.
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            source = directory / "a file.pdf"
            source.write_bytes(b"%PDF")
            incoming = [str(source)]
            existing: list[str] = []

            # When: picker/drop candidates are added through the shared contract.
            result = add_input_paths(
                incoming,
                existing,
                SUPPORTED_EXTENSIONS,
                is_busy=False,
                output_directory="",
            )

            # Then: the result is immutable, state inputs stay untouched, and the parent defaults.
            self.assertEqual(result.accepted, (source.resolve(),))
            self.assertEqual(result.selection, (source.resolve(),))
            self.assertEqual(result.output_directory, directory.resolve())
            self.assertEqual(incoming, [str(source)])
            self.assertEqual(existing, [])

    def test_reports_existing_and_incoming_duplicates_in_candidate_order(self) -> None:
        # Given: an existing selected PDF and a new PDF repeated in one picker/drop batch.
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            existing = directory / "existing.pdf"
            added = directory / "added.pdf"
            existing.write_bytes(b"%PDF")
            added.write_bytes(b"%PDF")

            # When: candidates repeat first an existing path and then a newly accepted path.
            result = add_input_paths(
                (str(existing), str(added), str(added)),
                (str(existing),),
                SUPPORTED_EXTENSIONS,
                is_busy=False,
                output_directory=None,
            )

            # Then: accepted and duplicate categories retain the original candidate order.
            self.assertEqual(result.accepted, (added.resolve(),))
            self.assertEqual(result.duplicates, (existing.resolve(), added.resolve()))

    def test_returns_busy_without_accepting_or_mutating_input_sequences(self) -> None:
        # Given: mutable caller sequences, a selected regular file, and an active conversion.
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            existing_file = directory / "existing.pdf"
            incoming_file = directory / "incoming.pdf"
            existing_file.write_bytes(b"%PDF")
            incoming_file.write_bytes(b"%PDF")
            incoming = [str(incoming_file)]
            existing = [str(existing_file)]

            # When: the picker/drop action runs while the GUI is busy.
            result = add_input_paths(
                incoming,
                existing,
                SUPPORTED_EXTENSIONS,
                is_busy=True,
                output_directory=directory,
            )

            # Then: nothing is accepted, input lists remain unchanged, and busy is explicit.
            self.assertEqual(result.accepted, ())
            self.assertEqual(result.busy, (incoming_file.resolve(),))
            self.assertEqual(result.selection, (existing_file.resolve(),))
            self.assertEqual(incoming, [str(incoming_file)])
            self.assertEqual(existing, [str(existing_file)])

    def test_preserves_multiple_file_order_and_uses_first_accept_for_blank_output(self) -> None:
        # Given: tuple-owned prior selection and two valid files from different parent folders.
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            prior = root / "prior.pdf"
            first_directory = root / "first folder"
            second_directory = root / "second folder"
            first_directory.mkdir()
            second_directory.mkdir()
            first = first_directory / "first.pdf"
            second = second_directory / "second.pdf"
            prior.write_bytes(b"%PDF")
            first.write_bytes(b"%PDF")
            second.write_bytes(b"%PDF")
            incoming = (str(first), str(second))
            existing = (str(prior),)

            # When: an idle picker/drop update has no output directory configured.
            result = add_input_paths(
                incoming,
                existing,
                SUPPORTED_EXTENSIONS,
                is_busy=False,
                output_directory="",
            )

            # Then: order, caller tuples, and the first newly accepted parent are preserved.
            self.assertEqual(result.accepted, (first.resolve(), second.resolve()))
            self.assertEqual(
                result.selection,
                (prior.resolve(), first.resolve(), second.resolve()),
            )
            self.assertEqual(result.output_directory, first_directory.resolve())
            self.assertEqual(incoming, (str(first), str(second)))
            self.assertEqual(existing, (str(prior),))


class TestTkDndSplitlistBoundary(unittest.TestCase):
    def test_preserves_spaced_paths_supplied_by_caller_splitlist_without_raw_parsing(self) -> None:
        # Given: the tuple produced by a caller's tk.splitlist(event.data) boundary call.
        split_paths = (r"C:\drop folder\a file.pdf", r"C:\drop folder\second file.md")

        # When: the pure helper receives those already-split entries.
        paths = input_paths_from_tkdnd_splitlist(split_paths)

        # Then: spaces are preserved and no whitespace or brace parsing is performed.
        self.assertEqual(paths, split_paths)

    def test_rejects_raw_event_data_string_instead_of_treating_characters_as_paths(self) -> None:
        # Given: unparsed Tcl event.data with a spaced filename enclosed in braces.
        raw_event_data = r"{C:\drop folder\a file.pdf}"

        # When: a caller bypasses tk.splitlist and passes the raw string directly.
        with self.assertRaises(TypeError):
            input_paths_from_tkdnd_splitlist(raw_event_data)

        # Then: the boundary rejects it instead of iterating the string character by character.


if __name__ == "__main__":
    unittest.main()
