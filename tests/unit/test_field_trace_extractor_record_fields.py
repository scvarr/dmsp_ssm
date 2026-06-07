from __future__ import annotations

import pytest

from dmsp_ssm._internal.format.definition import FormatDefinition
from dmsp_ssm._internal.format.raw_trace_reader import read_raw_int
from dmsp_ssm._internal.pipeline.field_trace_extractor import (
    extract_record_field_traces,
)

pytestmark = pytest.mark.unit


def test_extract_record_field_traces_builds_header_year_trace() -> None:
    format_definition = FormatDefinition()
    definition = format_definition.as_dict()
    chunk = bytearray(definition["record_size"])

    year_field = next(field for field in definition["header"] if field["name"] == "year")
    start = int(year_field["offset"])
    end = start + int(year_field["size"])
    chunk[start:end] = (2021).to_bytes(year_field["size"], byteorder="big", signed=True)

    traces = extract_record_field_traces(
        chunk=bytes(chunk),
        record_index=7,
        format_definition=format_definition,
    )
    by_name = {trace.field_name: trace for trace in traces}
    year_trace = by_name["year"]

    assert year_trace.record_index == 7
    assert year_trace.second_index is None
    assert year_trace.section == "header"
    assert year_trace.field_role == "record"
    assert year_trace.field_name == "year"
    assert year_trace.byte_offset == year_field["offset"]
    assert year_trace.byte_length == year_field["size"]
    assert year_trace.raw_hex == "000007E5"
    assert year_trace.raw_int == read_raw_int(
        chunk=bytes(chunk),
        byte_offset=year_field["offset"],
        byte_length=year_field["size"],
        byte_order=definition["byte_order"],
    )
    assert year_trace.unit == "year"


def test_extract_record_field_traces_excludes_second_level_fields() -> None:
    format_definition = FormatDefinition()
    definition = format_definition.as_dict()
    chunk = bytes(definition["record_size"])

    traces = extract_record_field_traces(
        chunk=chunk,
        record_index=0,
        format_definition=format_definition,
    )
    field_names = {trace.field_name for trace in traces}

    assert "time" not in field_names
    assert "bx" not in field_names
    assert "by" not in field_names
    assert "bz" not in field_names


def test_extract_record_field_traces_keeps_deterministic_header_order() -> None:
    format_definition = FormatDefinition()
    definition = format_definition.as_dict()
    chunk = bytes(definition["record_size"])

    traces = extract_record_field_traces(
        chunk=chunk,
        record_index=0,
        format_definition=format_definition,
    )
    header_names = [trace.field_name for trace in traces if trace.section == "header"]

    assert header_names[:3] == [
        definition["header"][0]["name"],
        definition["header"][1]["name"],
        definition["header"][2]["name"],
    ]


def test_extract_record_field_traces_transfers_units_from_format_definition() -> None:
    format_definition = FormatDefinition()
    definition = format_definition.as_dict()
    chunk = bytes(definition["record_size"])

    traces = extract_record_field_traces(
        chunk=chunk,
        record_index=0,
        format_definition=format_definition,
    )
    by_name = {trace.field_name: trace for trace in traces}

    assert by_name["day_of_year"].unit == "day"
    assert by_name["geodetic_latitude"].unit == "degree"
    assert by_name["geographic_longitude"].unit == "degree"
    assert by_name["altitude_km"].unit == "km"
    assert by_name["flight_number"].unit == "1"
