from __future__ import annotations

import pytest

from dmsp_ssm._internal.format.definition import FormatDefinition
from dmsp_ssm._internal.format.raw_trace_reader import read_raw_int
from dmsp_ssm._internal.pipeline.field_trace_extractor import (
    extract_second_field_traces,
)

pytestmark = pytest.mark.unit


def test_extract_second_field_traces_builds_first_second_time_trace() -> None:
    format_definition = FormatDefinition()
    definition = format_definition.as_dict()
    chunk = bytearray(definition["record_size"])
    second_block = next(
        block for block in definition["blocks"] if block["name"] == "second_data"
    )
    time_field = next(field for field in second_block["fields"] if field["name"] == "time")

    base_offset = int(second_block["start_offset"])
    byte_offset = base_offset + int(time_field["offset"])
    byte_length = int(time_field["size"])
    chunk[byte_offset:byte_offset + byte_length] = (12345).to_bytes(
        byte_length,
        byteorder="big",
        signed=True,
    )

    traces = extract_second_field_traces(
        chunk=bytes(chunk),
        record_index=3,
        format_definition=format_definition,
    )
    first_time_trace = next(
        trace
        for trace in traces
        if trace.second_index == 0 and trace.field_name == "time"
    )

    assert first_time_trace.record_index == 3
    assert first_time_trace.second_index == 0
    assert first_time_trace.section == "second_data"
    assert first_time_trace.field_role == "second"
    assert first_time_trace.field_name == "time"
    assert first_time_trace.byte_offset == byte_offset
    assert first_time_trace.byte_length == byte_length
    assert first_time_trace.raw_hex == "00003039"
    assert first_time_trace.raw_int == read_raw_int(
        chunk=bytes(chunk),
        byte_offset=byte_offset,
        byte_length=byte_length,
        byte_order=definition["byte_order"],
    )
    assert first_time_trace.unit == "s"


def test_extract_second_field_traces_contains_expected_first_second_fields() -> None:
    format_definition = FormatDefinition()
    definition = format_definition.as_dict()
    chunk = bytes(definition["record_size"])

    traces = extract_second_field_traces(
        chunk=chunk,
        record_index=0,
        format_definition=format_definition,
    )
    first_second_names = [
        trace.field_name
        for trace in traces
        if trace.section == "second_data" and trace.second_index == 0
    ]
    field_names = {trace.field_name for trace in traces}

    assert "year" not in field_names
    assert "day_of_year" not in field_names
    assert "flight_number" not in field_names

    expected_order = [
        field["name"]
        for field in next(
            block for block in definition["blocks"] if block["name"] == "second_data"
        )["fields"]
    ]
    assert first_second_names == expected_order
    for expected_name in ("time", "bx", "by", "bz"):
        if expected_name in expected_order:
            assert expected_name in first_second_names


def test_extract_second_field_traces_cover_multiple_seconds_in_order() -> None:
    format_definition = FormatDefinition()
    definition = format_definition.as_dict()
    chunk = bytes(definition["record_size"])

    traces = extract_second_field_traces(
        chunk=chunk,
        record_index=0,
        format_definition=format_definition,
    )
    second_indices = [trace.second_index for trace in traces]

    assert second_indices
    assert second_indices[0] == 0
    assert second_indices.count(0) == len(
        next(block for block in definition["blocks"] if block["name"] == "second_data")[
            "fields"
        ]
    )
    assert 1 in second_indices


def test_extract_second_field_traces_transfers_units_from_format_definition() -> None:
    format_definition = FormatDefinition()
    definition = format_definition.as_dict()
    chunk = bytes(definition["record_size"])

    traces = extract_second_field_traces(
        chunk=chunk,
        record_index=0,
        format_definition=format_definition,
    )
    first_second_by_name = {
        trace.field_name: trace
        for trace in traces
        if trace.second_index == 0
    }

    assert first_second_by_name["time"].unit == "s"
    assert first_second_by_name["bx"].unit == "nT"
    assert first_second_by_name["by"].unit == "nT"
    assert first_second_by_name["bz"].unit == "nT"
