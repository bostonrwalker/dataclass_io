from csv import DictReader
from dataclasses import dataclass
from dataclasses import fields
from io import TextIOWrapper
from pathlib import Path
from types import TracebackType
from typing import IO
from typing import Any
from typing import Optional
from typing import TextIO
from typing import Type
from typing import TypeAlias

from dataclass_io._lib.assertions import assert_dataclass_is_valid
from dataclass_io._lib.assertions import assert_file_is_readable
from dataclass_io._lib.dataclass_extensions import DataclassInstance

ReadableFileHandle: TypeAlias = TextIOWrapper | IO | TextIO


@dataclass(frozen=True, kw_only=True)
class FileHeader:
    """
    Header of a file.

    A file's header contains an optional preface, consisting of lines prefixed by a comment
    character and/or empty lines, and a required row of fieldnames before the data rows begin.

    Attributes:
        preface: A list of any lines preceding the fieldnames.
        fieldnames: The field names specified in the final line of the header.
    """

    preface: list[str]
    fieldnames: list[str]


class DataclassReader:
    def __init__(
        self,
        path: Path,
        dataclass_type: type[DataclassInstance],
        delimiter: str = "\t",
        header_comment_char: str = "#",
        **kwds: Any,
    ) -> None:
        """
        Args:
            path: Path to the file to read.
            dataclass_type: Dataclass type.

        Raises:
            FileNotFoundError: If the input file does not exist.
            IsADirectoryError: If the input file path is a directory.
            PermissionError: If the input file is not readable.
            TypeError: If the provided type is not a dataclass.
        """

        assert_file_is_readable(path)
        assert_dataclass_is_valid(dataclass_type)

        self.dataclass_type = dataclass_type
        self.delimiter = delimiter
        self.header_comment_char = header_comment_char

        self._fin = path.open("r")

        self._header = self._get_header(self._fin)
        if self._header is None:
            raise ValueError(f"Could not find a header in the provided file: {path}")

        if self._header.fieldnames != [f.name for f in fields(dataclass_type)]:
            raise ValueError(
                "The provided file does not have the same field names as the provided dataclass:\n"
                f"\tDataclass: {dataclass_type.__name__}\n"
                f"\tFile: {path}\n"
                f"\tDataclass fields: {dataclass_type.__name__}\n"
                f"\tFile: {path}\n"
            )

        self._reader = DictReader(
            self._fin,
            fieldnames=self._header.fieldnames,
            delimiter=self.delimiter,
        )

    def __enter__(self) -> "DataclassReader":
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException],
        exc_value: BaseException,
        traceback: TracebackType,
    ) -> None:
        self._fin.close()

    def __iter__(self) -> "DataclassReader":
        return self

    def __next__(self) -> DataclassInstance:
        row = next(self._reader)

        return self._row_to_dataclass(row)

    def _row_to_dataclass(self, row: dict[str, str]) -> DataclassInstance:
        """
        Convert a row of a CSV file into a dataclass instance.
        """

        coerced_values: dict[str, Any] = {}

        # Coerce each value in the row to the type of the corresponding field
        for field in fields(self.dataclass_type):
            value = row[field.name]
            coerced_values[field.name] = field.type(value)

        return self.dataclass_type(**coerced_values)

    def _get_header(
        self,
        reader: ReadableFileHandle,
    ) -> Optional[FileHeader]:
        """
        Read the header from an open file.

        The first row after any commented or empty lines will be used as the fieldnames.

        Lines preceding the fieldnames will be returned in the `preface.`

        NB: This function returns `Optional` instead of raising an error because the name of the
        source file is not in scope, making it difficult to provide a helpful error message. It is
        the responsibility of the caller to raise an error if the file is empty.

        See original proof-of-concept here: https://github.com/fulcrumgenomics/fgpyo/pull/103

        Args:
            reader: An open, readable file handle.
            comment_char: The character which indicates the start of a comment line.

        Returns:
            A `FileHeader` containing the field names and any preceding lines.
            None if the file was empty or contained only comments or empty lines.
        """

        preface: list[str] = []

        for line in reader:
            if line.startswith(self.header_comment_char) or line.strip() == "":
                preface.append(line.strip())
            else:
                break
        else:
            return None

        fieldnames = line.strip().split(self.delimiter)

        return FileHeader(preface=preface, fieldnames=fieldnames)