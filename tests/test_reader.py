from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest

from dataclass_io.reader import DataclassReader


@pytest.mark.parametrize("kw_only", [True, False])
@pytest.mark.parametrize("eq", [True, False])
@pytest.mark.parametrize("frozen", [True, False])
def test_reader(kw_only: bool, eq: bool, frozen: bool, tmp_path: Path) -> None:
    fpath = tmp_path / "test.txt"

    @dataclass(frozen=frozen, eq=eq, kw_only=kw_only)  # type: ignore[literal-required]
    class FakeDataclass:
        foo: str
        bar: int

    with fpath.open("w") as f:
        f.write("foo\tbar\n")
        f.write("abc\t1\n")

    rows: list[FakeDataclass]
    with DataclassReader.open(filename=fpath, dataclass_type=FakeDataclass) as reader:
        # TODO make `DataclassReader` generic
        rows = cast(list[FakeDataclass], [row for row in reader])

    assert len(rows) == 1

    if eq:
        assert rows[0] == FakeDataclass(foo="abc", bar=1)
    else:
        assert isinstance(rows[0], FakeDataclass)
        assert rows[0].foo == "abc"
        assert rows[0].bar == 1


def test_read_csv_with_header_quotes(tmp_path: Path) -> None:
    """
    Test that having quotes around column names in header row doesn't break anything
    https://github.com/msto/dataclass_io/issues/19
    """
    fpath = tmp_path / "test.txt"

    @dataclass
    class FakeDataclass:
        id: str
        title: str

    test_csv = [
        '"id"\t"title"\n',
        '"fake"\t"A fake object"\n',
        '"also_fake"\t"Another fake object"\n',
    ]

    with fpath.open("w") as f:
        f.writelines(test_csv)

    # Parse CSV using DataclassReader
    with DataclassReader.open(fpath, FakeDataclass) as reader:
        for fake_object in reader:
            print(fake_object)
