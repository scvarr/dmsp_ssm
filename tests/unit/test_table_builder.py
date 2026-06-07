from __future__ import annotations

import pytest

from dmsp_ssm._internal.builder.table_builder import TableBuilder
from dmsp_ssm._internal.pipeline.decoded_record import DecodedRecord
from dmsp_ssm._internal.pipeline.field_trace import FieldTrace

pytestmark = pytest.mark.unit

TABLE_TRACE_REQUIRED_COLUMNS = {
    "record_index",
    "second_index",
    "section",
    "field_name",
    "field_role",
    "byte_offset",
    "byte_length",
    "raw_hex",
    "raw_int",
    "decoded_value",
    "normalized_value",
    "unit",
    "transform",
    "valid",
}


def _record_trace() -> FieldTrace:
    return FieldTrace(
        record_index=0,
        second_index=None,
        section="header",
        field_name="year",
        field_role="record",
        byte_offset=0,
        byte_length=4,
        raw_hex="000007E5",
        raw_int=2021,
        unit=None,
        transform=None,
    )


def _second_trace() -> FieldTrace:
    return FieldTrace(
        record_index=0,
        second_index=3,
        section="second_data",
        field_name="bx",
        field_role="second",
        byte_offset=28,
        byte_length=4,
        raw_hex="0000002A",
        raw_int=42,
        unit="nT",
        transform="float(i)",
    )


def _decoded_records() -> list[DecodedRecord]:
    return [
        DecodedRecord(
            header={
                "year": 2021,
                "day_of_year": 42,
                "first_minute_first_second_time": 600,
                "geodetic_latitude": 10.5,
                "geographic_longitude": 20.5,
                "altitude_km": 850.0,
            },
            blocks={
                "second_data": [
                    {"time": -1000.0, "bx": 11.0, "by": 12.0, "bz": 13.0},
                    {"time": 2.0, "bx": 21.0, "by": 22.0, "bz": 23.0},
                ]
            },
            footer={"flight_number": 9},
        )
    ]


def _decoded_records_with_result_level_names() -> list[DecodedRecord]:
    return [
        DecodedRecord(
            header={
                "year": 2021,
                "day_of_year": 42,
                "minute_start_sec_of_day": 2.579,
                "latitude_deg": -81.49,
                "longitude_deg": 3.32,
                "altitude_km": 850.0,
            },
            blocks={
                "second_data": [
                    {"time": 1.0, "bx": 11.0, "by": 12.0, "bz": 13.0},
                ]
            },
            footer={"flight_number": 9},
        )
    ]


def _decoded_record_without_second_data() -> list[DecodedRecord]:
    return [
        DecodedRecord(
            header={"year": 2021},
            blocks={},
            footer={},
        )
    ]


def test_table_builder_returns_long_format_rows_with_required_keys() -> None:
    builder = TableBuilder()
    trace = _record_trace()

    rows = builder.build(field_traces=[trace])

    assert isinstance(rows, list)
    assert len(rows) == 1
    row = rows[0]
    assert set(row) == TABLE_TRACE_REQUIRED_COLUMNS
    assert row["record_index"] == trace.record_index
    assert row["second_index"] is None
    assert row["section"] == trace.section
    assert row["field_name"] == trace.field_name
    assert row["field_role"] == trace.field_role
    assert row["byte_offset"] == trace.byte_offset
    assert row["byte_length"] == trace.byte_length
    assert row["raw_hex"] == trace.raw_hex
    assert row["raw_int"] == trace.raw_int
    assert row["unit"] == trace.unit
    assert row["transform"] == trace.transform
    assert row["decoded_value"] is None
    assert row["normalized_value"] is None
    assert row["valid"] is True


def test_table_builder_preserves_input_order_for_multiple_traces() -> None:
    builder = TableBuilder()
    first = _record_trace()
    second = _second_trace()

    rows = builder.build(field_traces=[first, second], decoded_records=[])

    assert [row["field_name"] for row in rows] == [first.field_name, second.field_name]
    assert rows[0]["second_index"] is None
    assert rows[1]["second_index"] == 3


@pytest.mark.parametrize(
    ("field_name", "expected"),
    [
        ("year", 2021),
        ("day_of_year", 42),
        ("minute_start_sec_of_day", 600),
        ("latitude_deg", 10.5),
        ("longitude_deg", 20.5),
        ("altitude_km", 850.0),
        ("flight_number", 9),
    ],
)
def test_table_builder_maps_record_level_decoded_value(
    field_name: str,
    expected: object,
) -> None:
    builder = TableBuilder()
    traces = [
        FieldTrace(
            record_index=0,
            second_index=None,
            section="header",
            field_name=field_name,
            field_role="record",
            byte_offset=0,
            byte_length=4,
            raw_hex="00000000",
            raw_int=0,
            unit=None,
            transform=None,
        )
    ]

    rows = builder.build(field_traces=traces, decoded_records=_decoded_records())

    assert rows[0]["decoded_value"] == expected
    assert rows[0]["normalized_value"] == expected
    assert rows[0]["valid"] is True


def test_table_builder_maps_second_level_decoded_value() -> None:
    builder = TableBuilder()
    trace = FieldTrace(
        record_index=0,
        second_index=1,
        section="second_data",
        field_name="bx",
        field_role="second",
        byte_offset=0,
        byte_length=4,
        raw_hex="0000000B",
        raw_int=11,
        unit=None,
        transform=None,
    )

    rows = builder.build(field_traces=[trace], decoded_records=_decoded_records())

    assert rows[0]["decoded_value"] == 21.0
    assert rows[0]["normalized_value"] == 21.0
    assert rows[0]["valid"] is True


def test_table_builder_returns_none_for_unknown_field() -> None:
    builder = TableBuilder()
    trace = FieldTrace(
        record_index=0,
        second_index=None,
        section="header",
        field_name="unknown_field",
        field_role="record",
        byte_offset=0,
        byte_length=4,
        raw_hex="00000000",
        raw_int=0,
        unit=None,
        transform=None,
    )

    rows = builder.build(field_traces=[trace], decoded_records=_decoded_records())

    assert rows[0]["decoded_value"] is None
    assert rows[0]["normalized_value"] is None
    assert rows[0]["valid"] is True


def test_table_builder_returns_none_for_out_of_range_record_index() -> None:
    builder = TableBuilder()
    trace = FieldTrace(
        record_index=3,
        second_index=None,
        section="header",
        field_name="year",
        field_role="record",
        byte_offset=0,
        byte_length=4,
        raw_hex="00000000",
        raw_int=0,
        unit=None,
        transform=None,
    )

    rows = builder.build(field_traces=[trace], decoded_records=_decoded_records())

    assert rows[0]["decoded_value"] is None
    assert rows[0]["normalized_value"] is None
    assert rows[0]["valid"] is True


def test_table_builder_returns_none_for_out_of_range_second_index() -> None:
    builder = TableBuilder()
    trace = FieldTrace(
        record_index=0,
        second_index=99,
        section="second_data",
        field_name="bx",
        field_role="second",
        byte_offset=0,
        byte_length=4,
        raw_hex="00000000",
        raw_int=0,
        unit=None,
        transform=None,
    )

    rows = builder.build(field_traces=[trace], decoded_records=_decoded_records())

    assert rows[0]["decoded_value"] is None
    assert rows[0]["normalized_value"] is None
    assert rows[0]["valid"] is True


def test_table_builder_keeps_skeleton_behavior_when_decoded_records_absent() -> None:
    builder = TableBuilder()
    trace = _record_trace()

    rows = builder.build(field_traces=[trace], decoded_records=None)

    assert rows[0]["decoded_value"] is None
    assert rows[0]["normalized_value"] is None
    assert rows[0]["valid"] is True


def test_table_builder_marks_missing_time_row_as_invalid_and_normalizes_to_none() -> None:
    builder = TableBuilder()
    trace = FieldTrace(
        record_index=0,
        second_index=0,
        section="second_data",
        field_name="time",
        field_role="second",
        byte_offset=0,
        byte_length=4,
        raw_hex="FFFFFC18",
        raw_int=-1000,
        unit=None,
        transform=None,
    )

    rows = builder.build(field_traces=[trace], decoded_records=_decoded_records())

    assert rows[0]["decoded_value"] == -1000.0
    assert rows[0]["normalized_value"] is None
    assert rows[0]["valid"] is False


def test_table_builder_marks_missing_second_bx_row_as_invalid_and_normalizes_to_none() -> None:
    builder = TableBuilder()
    trace = FieldTrace(
        record_index=0,
        second_index=0,
        section="second_data",
        field_name="bx",
        field_role="second",
        byte_offset=0,
        byte_length=4,
        raw_hex="0000000B",
        raw_int=11,
        unit=None,
        transform=None,
    )

    rows = builder.build(field_traces=[trace], decoded_records=_decoded_records())

    assert rows[0]["decoded_value"] == 11.0
    assert rows[0]["normalized_value"] is None
    assert rows[0]["valid"] is False


def test_table_builder_keeps_record_level_valid_true_even_when_record_has_missing_seconds() -> None:
    builder = TableBuilder()
    trace = _record_trace()

    rows = builder.build(field_traces=[trace], decoded_records=_decoded_records())

    assert rows[0]["decoded_value"] == 2021
    assert rows[0]["normalized_value"] == 2021
    assert rows[0]["valid"] is True


def test_table_builder_unknown_second_level_field_stays_valid_true() -> None:
    builder = TableBuilder()
    trace = FieldTrace(
        record_index=0,
        second_index=0,
        section="second_data",
        field_name="unknown_second_field",
        field_role="second",
        byte_offset=0,
        byte_length=4,
        raw_hex="00000000",
        raw_int=0,
        unit=None,
        transform=None,
    )

    rows = builder.build(field_traces=[trace], decoded_records=_decoded_records())

    assert rows[0]["decoded_value"] is None
    assert rows[0]["normalized_value"] is None
    assert rows[0]["valid"] is True


def test_table_builder_second_level_field_with_absent_second_data_block_falls_back_to_none() -> None:
    builder = TableBuilder()
    trace = FieldTrace(
        record_index=0,
        second_index=0,
        section="second_data",
        field_name="bx",
        field_role="second",
        byte_offset=0,
        byte_length=4,
        raw_hex="00000000",
        raw_int=0,
        unit=None,
        transform=None,
    )

    rows = builder.build(
        field_traces=[trace],
        decoded_records=_decoded_record_without_second_data(),
    )

    assert rows[0]["decoded_value"] is None
    assert rows[0]["normalized_value"] is None
    assert rows[0]["valid"] is True


def test_table_builder_second_level_field_with_missing_time_marker_undefined_stays_valid() -> None:
    builder = TableBuilder()
    trace = FieldTrace(
        record_index=0,
        second_index=0,
        section="second_data",
        field_name="bx",
        field_role="second",
        byte_offset=0,
        byte_length=4,
        raw_hex="0000000B",
        raw_int=11,
        unit=None,
        transform=None,
    )
    decoded_records = [
        DecodedRecord(
            header={"year": 2021},
            blocks={"second_data": [{"bx": 11.0}]},
            footer={},
        )
    ]

    rows = builder.build(field_traces=[trace], decoded_records=decoded_records)

    assert rows[0]["decoded_value"] == 11.0
    assert rows[0]["normalized_value"] == 11.0
    assert rows[0]["valid"] is True


def test_table_builder_second_level_field_with_non_numeric_time_stays_valid() -> None:
    builder = TableBuilder()
    trace = FieldTrace(
        record_index=0,
        second_index=0,
        section="second_data",
        field_name="bx",
        field_role="second",
        byte_offset=0,
        byte_length=4,
        raw_hex="0000000B",
        raw_int=11,
        unit=None,
        transform=None,
    )
    decoded_records = [
        DecodedRecord(
            header={"year": 2021},
            blocks={"second_data": [{"time": "bad-time", "bx": 11.0}]},
            footer={},
        )
    ]

    rows = builder.build(field_traces=[trace], decoded_records=decoded_records)

    assert rows[0]["decoded_value"] == 11.0
    assert rows[0]["normalized_value"] == 11.0
    assert rows[0]["valid"] is True


@pytest.mark.parametrize(
    ("trace_field_name", "expected"),
    [
        ("first_minute_first_second_time", 2.579),
        ("geodetic_latitude", -81.49),
        ("geographic_longitude", 3.32),
        ("altitude", 850.0),
        ("year", 2021),
        ("day_of_year", 42),
    ],
)
def test_table_builder_maps_record_level_aliases_from_raw_trace_name_to_decoded_names(
    trace_field_name: str,
    expected: object,
) -> None:
    builder = TableBuilder()
    trace = FieldTrace(
        record_index=0,
        second_index=None,
        section="header",
        field_name=trace_field_name,
        field_role="record",
        byte_offset=0,
        byte_length=4,
        raw_hex="00000000",
        raw_int=0,
        unit=None,
        transform=None,
    )

    rows = builder.build(
        field_traces=[trace],
        decoded_records=_decoded_records_with_result_level_names(),
    )

    assert rows[0]["decoded_value"] == expected
    assert rows[0]["normalized_value"] == expected
    assert rows[0]["valid"] is True
