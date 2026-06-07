import gzip
from pathlib import Path

import pytest

from dmsp_ssm._internal.source import DataSource

pytestmark = pytest.mark.integration


def _read_all_source_bytes(source: DataSource) -> bytes:
    source_files = source.list_source_files()
    return b"".join(source.read_source_file(source_file) for source_file in source_files)


def test_per_file_api_reads_content_of_dat_file(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.dat"
    file_path.write_bytes(b"abc")

    source = DataSource(file_path)

    assert _read_all_source_bytes(source) == b"abc"


def test_per_file_api_reads_uncompressed_content_of_gz_file(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.gz"
    with gzip.open(file_path, "wb") as stream:
        stream.write(b"abc")

    source = DataSource(file_path)

    assert _read_all_source_bytes(source) == b"abc"


def test_per_file_api_concatenates_dat_files_from_directory_in_sorted_order(
    tmp_path: Path,
) -> None:
    (tmp_path / "b.dat").write_bytes(b"222")
    (tmp_path / "a.dat").write_bytes(b"111")

    source = DataSource(tmp_path)

    assert _read_all_source_bytes(source) == b"111222"


def test_per_file_api_concatenates_gz_files_from_directory_in_sorted_order(
    tmp_path: Path,
) -> None:
    with gzip.open(tmp_path / "b.gz", "wb") as stream:
        stream.write(b"222")
    with gzip.open(tmp_path / "a.gz", "wb") as stream:
        stream.write(b"111")

    source = DataSource(tmp_path)

    assert _read_all_source_bytes(source) == b"111222"


def test_list_source_files_raises_value_error_for_empty_directory(tmp_path: Path) -> None:
    source = DataSource(tmp_path)

    with pytest.raises(ValueError):
        source.list_source_files()


def test_list_source_files_raises_value_error_for_mixed_dat_and_gz_files(
    tmp_path: Path,
) -> None:
    (tmp_path / "a.dat").write_bytes(b"111")
    with gzip.open(tmp_path / "b.gz", "wb") as stream:
        stream.write(b"222")

    source = DataSource(tmp_path)

    with pytest.raises(ValueError):
        source.list_source_files()


def test_list_source_files_raises_value_error_for_unsupported_files(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")

    source = DataSource(tmp_path)

    with pytest.raises(ValueError):
        source.list_source_files()


def test_per_file_api_raises_file_not_found_for_missing_path() -> None:
    missing_path = Path("/path/does/not/exist.dat")
    source = DataSource(missing_path)

    with pytest.raises(FileNotFoundError):
        _read_all_source_bytes(source)


def test_data_source_reads_dat_files_recursively(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()

    file_b = root / "b.dat"
    file_b.write_bytes(b"B")

    nested = root / "nested"
    nested.mkdir()

    file_a = nested / "a.dat"
    file_a.write_bytes(b"A")

    source = DataSource(root, recursive=True)

    assert _read_all_source_bytes(source) == b"BA"


def test_data_source_reads_gz_files_recursively(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()

    with gzip.open(root / "b.gz", "wb") as stream:
        stream.write(b"B")

    nested = root / "nested"
    nested.mkdir()

    with gzip.open(nested / "a.gz", "wb") as stream:
        stream.write(b"A")

    source = DataSource(root, recursive=True)

    assert _read_all_source_bytes(source) == b"BA"


def test_data_source_raises_error_for_mixed_file_types_when_recursive(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "a.dat").write_bytes(b"A")

    nested = root / "nested"
    nested.mkdir()
    with gzip.open(nested / "b.gz", "wb") as stream:
        stream.write(b"B")

    source = DataSource(root, recursive=True)

    with pytest.raises(ValueError, match="смешанные типы файлов"):
        source.list_source_files()


def test_data_source_raises_error_for_recursively_empty_directory(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "nested").mkdir()

    source = DataSource(root, recursive=True)

    with pytest.raises(ValueError, match="Каталог пустой"):
        source.list_source_files()
