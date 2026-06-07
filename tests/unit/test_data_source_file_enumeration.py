from pathlib import Path
from typing import cast

import pytest

from dmsp_ssm._internal.source.data_source import (
    DataSource,
    SourceFile,
)

pytestmark = pytest.mark.unit


def test_list_source_files_returns_single_dat_file(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.dat"
    file_path.write_bytes(b"payload")

    source = DataSource(file_path)

    files = source.list_source_files()

    assert len(files) == 1
    assert files[0].path == file_path
    assert files[0].kind == "dat"


def test_list_source_files_returns_single_gz_file(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.gz"
    file_path.write_bytes(b"payload")

    source = DataSource(file_path)

    files = source.list_source_files()

    assert len(files) == 1
    assert files[0].path == file_path
    assert files[0].kind == "gz"


def test_list_source_files_returns_flat_directory_dat_files_in_sorted_order(
    tmp_path: Path,
) -> None:
    (tmp_path / "b.dat").write_bytes(b"B")
    (tmp_path / "a.dat").write_bytes(b"A")

    source = DataSource(tmp_path)

    files = source.list_source_files()

    assert [file.path.name for file in files] == ["a.dat", "b.dat"]
    assert all(file.kind == "dat" for file in files)


def test_list_source_files_returns_recursive_directory_files_in_relative_path_order(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    root.mkdir()

    late_dir = root / "f12" / "ssm" / "2002" / "10"
    late_dir.mkdir(parents=True)
    (late_dir / "b.dat").write_bytes(b"B")

    early_dir = root / "f12" / "ssm" / "2002" / "02"
    early_dir.mkdir(parents=True)
    (early_dir / "a.dat").write_bytes(b"A")

    source = DataSource(root, recursive=True)

    files = source.list_source_files()

    assert [file.path.relative_to(root).as_posix() for file in files] == [
        "f12/ssm/2002/02/a.dat",
        "f12/ssm/2002/10/b.dat",
    ]
    assert all(file.kind == "dat" for file in files)


def test_list_source_files_raises_for_mixed_dat_and_gz_files(tmp_path: Path) -> None:
    (tmp_path / "a.dat").write_bytes(b"A")
    (tmp_path / "b.gz").write_bytes(b"B")

    source = DataSource(tmp_path)

    with pytest.raises(ValueError, match="смешанные типы"):
        source.list_source_files()


def test_list_source_files_raises_for_unsupported_extension_in_directory(
    tmp_path: Path,
) -> None:
    (tmp_path / "a.dat").write_bytes(b"A")
    (tmp_path / "note.txt").write_text("unsupported", encoding="utf-8")

    source = DataSource(tmp_path)

    with pytest.raises(ValueError, match="неподдерживаемые"):
        source.list_source_files()


def test_list_source_files_raises_for_empty_directory(tmp_path: Path) -> None:
    source = DataSource(tmp_path)

    with pytest.raises(ValueError, match="Каталог пустой"):
        source.list_source_files()


def test_list_source_files_raises_for_recursive_directory_without_files(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "nested").mkdir()

    source = DataSource(root, recursive=True)

    with pytest.raises(ValueError, match="Каталог пустой"):
        source.list_source_files()


def test_read_source_file_reads_dat_bytes(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.dat"
    file_path.write_bytes(b"dat-payload")
    source = DataSource(file_path)

    file_descriptor = SourceFile(path=file_path, kind="dat")

    result = source.read_source_file(file_descriptor)

    assert result == b"dat-payload"


def test_read_source_file_reads_uncompressed_gz_bytes(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.gz"
    source = DataSource(file_path)

    import gzip

    with gzip.open(file_path, "wb") as stream:
        stream.write(b"gz-payload")

    file_descriptor = SourceFile(path=file_path, kind="gz")

    result = source.read_source_file(file_descriptor)

    assert result == b"gz-payload"


def test_read_source_file_raises_for_unsupported_descriptor_kind(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "sample.dat"
    file_path.write_bytes(b"payload")
    source = DataSource(file_path)

    class FakeSourceFile:
        def __init__(self, path: Path, kind: str):
            self.path = path
            self.kind = kind

    invalid_descriptor = cast(SourceFile, FakeSourceFile(path=file_path, kind="txt"))

    with pytest.raises(ValueError, match="Неподдерживаемый тип source file"):
        source.read_source_file(invalid_descriptor)


def test_list_source_files_is_deterministic_between_repeated_calls(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    root.mkdir()

    path_b = root / "f12" / "ssm" / "2002" / "10"
    path_b.mkdir(parents=True)
    (path_b / "b.dat").write_bytes(b"B")

    path_a = root / "f12" / "ssm" / "2002" / "02"
    path_a.mkdir(parents=True)
    (path_a / "a.dat").write_bytes(b"A")

    source = DataSource(root, recursive=True)

    first = source.list_source_files()
    second = source.list_source_files()

    assert [file.path.relative_to(root).as_posix() for file in first] == [
        "f12/ssm/2002/02/a.dat",
        "f12/ssm/2002/10/b.dat",
    ]
    assert [
        file.path.relative_to(root).as_posix() for file in first
    ] == [
        file.path.relative_to(root).as_posix() for file in second
    ]
