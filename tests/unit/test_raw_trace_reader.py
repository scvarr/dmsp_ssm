import pytest

from dmsp_ssm._internal.format.raw_field_reader import BinaryFieldReader
from dmsp_ssm._internal.format.raw_trace_reader import (
    read_raw_hex,
    read_raw_int,
)

pytestmark = pytest.mark.unit


def test_read_raw_hex_returns_uppercase_hex_without_prefix() -> None:
    chunk = bytes([0x00, 0x07, 0xE5, 0xFF])

    assert read_raw_hex(chunk=chunk, byte_offset=1, byte_length=2) == "07E5"


def test_read_raw_int_reads_big_endian_by_project_policy() -> None:
    chunk = bytes([0x00, 0x00, 0x07, 0xE5])

    assert read_raw_int(
        chunk=chunk,
        byte_offset=0,
        byte_length=4,
        byte_order="big",
    ) == 2021


def test_read_raw_hex_rejects_negative_offset() -> None:
    with pytest.raises(ValueError, match="byte_offset"):
        read_raw_hex(chunk=b"\x00\x01", byte_offset=-1, byte_length=1)


def test_read_raw_hex_rejects_non_positive_length() -> None:
    with pytest.raises(ValueError, match="byte_length"):
        read_raw_hex(chunk=b"\x00\x01", byte_offset=0, byte_length=0)


def test_read_raw_hex_rejects_slice_overflow() -> None:
    with pytest.raises(ValueError, match="границы chunk"):
        read_raw_hex(chunk=b"\x00\x01", byte_offset=1, byte_length=2)


def test_read_raw_int_rejects_unsupported_byte_order() -> None:
    with pytest.raises(ValueError, match="Неподдерживаемый byte_order"):
        read_raw_int(
            chunk=b"\x00\x00\x07\xE5",
            byte_offset=0,
            byte_length=4,
            byte_order="middle",
        )


def test_read_raw_int_matches_binary_field_reader_policy() -> None:
    chunk = bytes([0x00, 0x00, 0x07, 0xE5, 0xFF, 0xFF, 0xFF, 0x9C])
    field_definition = {
        "name": "year",
        "offset": 4,
        "size": 4,
        "type": "int",
    }
    reader = BinaryFieldReader(byte_order="big")

    expected = reader.read_raw_int(record=chunk, field_definition=field_definition)
    actual = read_raw_int(
        chunk=chunk,
        byte_offset=4,
        byte_length=4,
        byte_order="big",
    )

    assert actual == expected
