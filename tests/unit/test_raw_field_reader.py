import pytest

from dmsp_ssm._internal.format.layout import build_field_definitions
from dmsp_ssm._internal.format.raw_field_reader import BinaryFieldReader

pytestmark = pytest.mark.unit


def test_binary_field_reader_reads_raw_integer_by_offset_and_size(
    ssm_format_definition: dict,
) -> None:
    field_definitions = build_field_definitions(ssm_format_definition)
    year_field = field_definitions["year"]
    day_field = field_definitions["day_of_year"]

    record = bytearray(ssm_format_definition["record_size"])
    record[0:4] = (2005).to_bytes(4, byteorder="big", signed=True)
    record[4:8] = (123).to_bytes(4, byteorder="big", signed=True)

    reader = BinaryFieldReader(byte_order=ssm_format_definition["byte_order"])

    assert reader.read_raw_int(record=bytes(record), field_definition=year_field) == 2005
    assert reader.read_raw_int(record=bytes(record), field_definition=day_field) == 123


def test_binary_field_reader_does_not_apply_transform(
    ssm_format_definition: dict,
) -> None:
    field_definitions = build_field_definitions(ssm_format_definition)
    latitude_field = field_definitions["geodetic_latitude"]

    record = bytearray(ssm_format_definition["record_size"])
    record[12:16] = (1234).to_bytes(4, byteorder="big", signed=True)

    reader = BinaryFieldReader(byte_order=ssm_format_definition["byte_order"])
    raw_value = reader.read_raw_int(
        record=bytes(record),
        field_definition=latitude_field,
    )

    assert raw_value == 1234


def test_binary_field_reader_rejects_unsupported_field_type(
    ssm_format_definition: dict,
) -> None:
    reader = BinaryFieldReader(byte_order=ssm_format_definition["byte_order"])
    field_definition = {
        "name": "geodetic_latitude",
        "offset": 12,
        "size": 4,
        "type": "float",
    }

    record = bytearray(ssm_format_definition["record_size"])
    record[12:16] = (1234).to_bytes(4, byteorder="big", signed=True)

    with pytest.raises(ValueError, match="Поддерживается только type='int'"):
        reader.read_raw_int(
            record=bytes(record),
            field_definition=field_definition,
        )
