from __future__ import annotations

import pytest

from dmsp_ssm._internal.format.definition import FormatDefinition
from dmsp_ssm._internal.pipeline.field_trace_extractor import (
    extract_field_traces,
)

pytestmark = pytest.mark.unit


def test_extract_field_traces_returns_record_and_second_level_fields() -> None:
    format_definition = FormatDefinition()
    definition = format_definition.as_dict()
    chunk = bytes(definition["record_size"])

    traces = extract_field_traces(
        chunk=chunk,
        record_index=11,
        format_definition=format_definition,
    )
    field_names = {trace.field_name for trace in traces}

    assert "year" in field_names
    assert "time" in field_names
    assert all(trace.record_index == 11 for trace in traces)


def test_extract_field_traces_keeps_unified_deterministic_order() -> None:
    format_definition = FormatDefinition()
    definition = format_definition.as_dict()
    chunk = bytes(definition["record_size"])

    traces = extract_field_traces(
        chunk=chunk,
        record_index=0,
        format_definition=format_definition,
    )

    header_count = len(definition.get("header", []))
    footer_count = len(definition.get("footer", []))
    second_fields_count = len(
        next(block for block in definition["blocks"] if block["name"] == "second_data")[
            "fields"
        ]
    )

    assert header_count > 0
    assert traces[0].section == "header"
    assert all(trace.section == "header" for trace in traces[:header_count])

    assert len(traces) > header_count
    first_second_index = header_count
    assert traces[first_second_index].section == "second_data"
    assert traces[first_second_index].second_index == 0
    assert all(
        trace.section == "second_data"
        for trace in traces[header_count:header_count + second_fields_count]
    )

    if footer_count > 0:
        footer_slice = traces[-footer_count:]
        assert all(trace.section == "footer" for trace in footer_slice)


def test_extract_field_traces_second_index_presence_matches_field_role() -> None:
    format_definition = FormatDefinition()
    definition = format_definition.as_dict()
    chunk = bytes(definition["record_size"])

    traces = extract_field_traces(
        chunk=chunk,
        record_index=5,
        format_definition=format_definition,
    )
    first_record_trace = next(trace for trace in traces if trace.field_role == "record")
    first_second_trace = next(trace for trace in traces if trace.field_role == "second")

    assert first_record_trace.second_index is None
    assert first_second_trace.second_index is not None
