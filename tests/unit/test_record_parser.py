import pytest

from dmsp_ssm._internal.pipeline.record_parser import RecordParser
from dmsp_ssm._internal.pipeline.raw_record import RawRecord

pytestmark = pytest.mark.unit


def test_record_parser_extracts_all_header_fields_by_layout(
    ssm_format_definition: dict,
) -> None:
    parser = RecordParser(format_definition=ssm_format_definition)

    record = bytearray(ssm_format_definition["record_size"])
    expected_header: dict[str, int] = {}
    for index, field_definition in enumerate(ssm_format_definition["header"], start=1):
        value = index * 10
        expected_header[field_definition["name"]] = value
        start = field_definition["offset"]
        end = start + field_definition["size"]
        record[start:end] = value.to_bytes(4, byteorder="big", signed=True)

    expected_footer: dict[str, int] = {}
    for index, field_definition in enumerate(ssm_format_definition["footer"], start=1):
        value = index * 1000
        expected_footer[field_definition["name"]] = value
        start = field_definition["offset"]
        end = start + field_definition["size"]
        record[start:end] = value.to_bytes(4, byteorder="big", signed=True)

    parsed = parser.parse_record(bytes(record))

    assert isinstance(parsed, RawRecord)
    assert parsed.raw_bytes == bytes(record)
    assert parsed.header == expected_header
    assert parsed.footer == expected_footer
    assert set(parsed.blocks) == {"second_data"}
    assert len(parsed.blocks["second_data"]) == 60


def test_record_parser_uses_injected_raw_field_reader(
    ssm_format_definition: dict,
) -> None:
    class FieldReaderSpy:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def read_raw_int(self, *, record: bytes, field_definition: dict) -> int:
            self.calls.append(field_definition["name"])
            return 1

    field_reader = FieldReaderSpy()
    parser = RecordParser(
        format_definition=ssm_format_definition,
        field_reader=field_reader,  # type: ignore[arg-type]
    )

    record = bytes(ssm_format_definition["record_size"])
    parsed = parser.parse_record(record)

    expected_calls = [field["name"] for field in ssm_format_definition["header"]]
    for block_definition in ssm_format_definition["blocks"]:
        for _ in range(block_definition["repeat"]):
            expected_calls.extend(
                field["name"] for field in block_definition.get("fields", [])
            )
    expected_calls.extend(
        field["name"] for field in ssm_format_definition["footer"]
    )
    assert field_reader.calls == expected_calls
    assert all(value == 1 for value in parsed.header.values())
    assert all(
        all(value == 1 for value in repeat.values())
        for repeats in parsed.blocks.values()
        for repeat in repeats
    )
    assert all(value == 1 for value in parsed.footer.values())


def test_record_parser_extracts_repeated_blocks_by_layout(
    ssm_format_definition: dict,
) -> None:
    parser = RecordParser(format_definition=ssm_format_definition)
    block_definition = ssm_format_definition["blocks"][0]
    block_fields = block_definition["fields"]

    record = bytearray(ssm_format_definition["record_size"])
    for repeat_index in range(block_definition["repeat"]):
        base_offset = block_definition["start_offset"] + (
            repeat_index * block_definition["stride"]
        )
        for field_index, field_definition in enumerate(block_fields, start=1):
            value = (repeat_index + 1) * 100 + field_index
            start = base_offset + field_definition["offset"]
            end = start + field_definition["size"]
            record[start:end] = value.to_bytes(4, byteorder="big", signed=True)

    parsed = parser.parse_record(bytes(record))
    parsed_repeats = parsed.blocks[block_definition["name"]]

    assert len(parsed_repeats) == block_definition["repeat"]
    for repeat_index, repeat_values in enumerate(parsed_repeats):
        for field_index, field_definition in enumerate(block_fields, start=1):
            expected = (repeat_index + 1) * 100 + field_index
            assert repeat_values[field_definition["name"]] == expected


def test_record_parser_extracts_footer_fields_by_layout(
    ssm_format_definition: dict,
) -> None:
    parser = RecordParser(format_definition=ssm_format_definition)
    record = bytearray(ssm_format_definition["record_size"])

    expected_footer: dict[str, int] = {}
    for index, field_definition in enumerate(ssm_format_definition["footer"], start=1):
        value = index * 77
        expected_footer[field_definition["name"]] = value
        start = field_definition["offset"]
        end = start + field_definition["size"]
        record[start:end] = value.to_bytes(4, byteorder="big", signed=True)

    parsed = parser.parse_record(bytes(record))
    assert parsed.footer == expected_footer


def test_record_parser_assembles_complete_raw_record_from_layout_sections(
    ssm_format_definition: dict,
) -> None:
    parser = RecordParser(format_definition=ssm_format_definition)
    record = bytearray(ssm_format_definition["record_size"])

    header_year = next(
        field for field in ssm_format_definition["header"] if field["name"] == "year"
    )
    record[
        header_year["offset"]:header_year["offset"] + header_year["size"]
    ] = (2040).to_bytes(4, byteorder="big", signed=True)

    block_definition = ssm_format_definition["blocks"][0]
    time_field = next(
        field for field in block_definition["fields"] if field["name"] == "time"
    )
    first_repeat_time_offset = block_definition["start_offset"] + time_field["offset"]
    record[
        first_repeat_time_offset:first_repeat_time_offset + time_field["size"]
    ] = (777).to_bytes(4, byteorder="big", signed=True)

    footer_flight_number = next(
        field
        for field in ssm_format_definition["footer"]
        if field["name"] == "flight_number"
    )
    record[
        footer_flight_number["offset"]:footer_flight_number["offset"] + footer_flight_number["size"]
    ] = (19).to_bytes(4, byteorder="big", signed=True)

    parsed = parser.parse_record(bytes(record))

    assert parsed.header["year"] == 2040
    assert parsed.blocks[block_definition["name"]][0]["time"] == 777
    assert parsed.footer["flight_number"] == 19


def test_record_parser_uses_shared_layout_reader_for_all_sections(
    ssm_format_definition: dict,
) -> None:
    class ParserSpy(RecordParser):
        def __init__(self, *, format_definition: dict) -> None:
            super().__init__(format_definition=format_definition)
            self.layout_calls: list[tuple[tuple[str, ...], int]] = []

        def _read_layout_fields(
            self,
            *,
            record: bytes,
            field_definitions: list[dict],
            base_offset: int = 0,
        ) -> dict[str, int | float | str]:
            self.layout_calls.append(
                (tuple(field["name"] for field in field_definitions), base_offset)
            )
            return super()._read_layout_fields(
                record=record,
                field_definitions=field_definitions,
                base_offset=base_offset,
            )

    parser = ParserSpy(format_definition=ssm_format_definition)
    parser.parse_record(bytes(ssm_format_definition["record_size"]))

    header_names = tuple(field["name"] for field in ssm_format_definition["header"])
    footer_names = tuple(field["name"] for field in ssm_format_definition["footer"])
    block_definition = ssm_format_definition["blocks"][0]
    block_names = tuple(field["name"] for field in block_definition["fields"])

    assert parser.layout_calls[0] == (header_names, 0)
    assert parser.layout_calls[-1] == (footer_names, 0)
    block_calls = parser.layout_calls[1:-1]
    assert len(block_calls) == block_definition["repeat"]
    assert all(names == block_names for names, _ in block_calls)
    assert block_calls[0][1] == block_definition["start_offset"]
    assert block_calls[-1][1] == (
        block_definition["start_offset"]
        + (block_definition["repeat"] - 1) * block_definition["stride"]
    )


def test_record_parser_returns_raw_values_without_transform_or_semantic_decode(
    ssm_format_definition: dict,
) -> None:
    parser = RecordParser(format_definition=ssm_format_definition)
    record = bytearray(ssm_format_definition["record_size"])

    header_with_transform = next(
        field
        for field in ssm_format_definition["header"]
        if field["name"] == "geodetic_latitude"
    )
    record[
        header_with_transform["offset"]:header_with_transform["offset"] + header_with_transform["size"]
    ] = (12345).to_bytes(4, byteorder="big", signed=True)

    block_definition = ssm_format_definition["blocks"][0]
    block_field_with_transform = next(
        field for field in block_definition["fields"] if field["name"] == "time"
    )
    block_time_offset = block_definition["start_offset"] + block_field_with_transform["offset"]
    record[
        block_time_offset:block_time_offset + block_field_with_transform["size"]
    ] = (60000).to_bytes(4, byteorder="big", signed=True)

    parsed = parser.parse_record(bytes(record))
    assert parsed.header["geodetic_latitude"] == 12345
    assert parsed.blocks[block_definition["name"]][0]["time"] == 60000


def test_record_parser_output_shape_follows_layout_contract(
    ssm_format_definition: dict,
) -> None:
    format_definition = {
        "record_size": 44,
        "byte_order": "big",
        "validation_fields": ["header_flag", "footer_code"],
        "header": [
            {"name": "header_flag", "offset": 0, "size": 4, "type": "int"},
            {"name": "header_seq", "offset": 4, "size": 4, "type": "int"},
        ],
        "blocks": [
            {
                "name": "alpha_block",
                "repeat": 2,
                "stride": 8,
                "start_offset": 8,
                "fields": [
                    {"name": "a_left", "offset": 0, "size": 4, "type": "int"},
                    {"name": "a_right", "offset": 4, "size": 4, "type": "int"},
                ],
            },
            {
                "name": "beta_block",
                "repeat": 3,
                "stride": 4,
                "start_offset": 24,
                "fields": [
                    {"name": "b_value", "offset": 0, "size": 4, "type": "int"},
                ],
            },
        ],
        "footer": [
            {"name": "footer_code", "offset": 40, "size": 4, "type": "int"},
        ],
    }
    parser = RecordParser(format_definition=format_definition)
    record = bytearray(format_definition["record_size"])

    record[0:4] = (101).to_bytes(4, byteorder="big", signed=True)
    record[4:8] = (202).to_bytes(4, byteorder="big", signed=True)

    record[8:12] = (11).to_bytes(4, byteorder="big", signed=True)
    record[12:16] = (12).to_bytes(4, byteorder="big", signed=True)
    record[16:20] = (21).to_bytes(4, byteorder="big", signed=True)
    record[20:24] = (22).to_bytes(4, byteorder="big", signed=True)

    record[24:28] = (31).to_bytes(4, byteorder="big", signed=True)
    record[28:32] = (32).to_bytes(4, byteorder="big", signed=True)
    record[32:36] = (33).to_bytes(4, byteorder="big", signed=True)

    record[40:44] = (909).to_bytes(4, byteorder="big", signed=True)

    parsed = parser.parse_record(bytes(record))

    assert set(parsed.header) == {"header_flag", "header_seq"}
    assert parsed.header["header_flag"] == 101
    assert parsed.header["header_seq"] == 202

    assert set(parsed.blocks) == {"alpha_block", "beta_block"}
    assert len(parsed.blocks["alpha_block"]) == 2
    assert parsed.blocks["alpha_block"][0] == {"a_left": 11, "a_right": 12}
    assert parsed.blocks["alpha_block"][1] == {"a_left": 21, "a_right": 22}
    assert len(parsed.blocks["beta_block"]) == 3
    assert parsed.blocks["beta_block"][0] == {"b_value": 31}
    assert parsed.blocks["beta_block"][1] == {"b_value": 32}
    assert parsed.blocks["beta_block"][2] == {"b_value": 33}

    assert set(parsed.footer) == {"footer_code"}
    assert parsed.footer["footer_code"] == 909


def test_record_parser_rejects_record_with_unexpected_size(
    ssm_format_definition: dict,
) -> None:
    parser = RecordParser(format_definition=ssm_format_definition)

    with pytest.raises(ValueError, match="Размер записи не совпадает"):
        parser.parse_record(b"\x00" * (ssm_format_definition["record_size"] - 1))
