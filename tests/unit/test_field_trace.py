from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from dmsp_ssm._internal.pipeline.field_trace import FieldTrace

pytestmark = pytest.mark.unit


def test_field_trace_can_be_created_for_record_level_field() -> None:
    trace = FieldTrace(
        record_index=0,
        second_index=None,
        section="header",
        field_name="year",
        field_role="record",
        byte_offset=0,
        byte_length=2,
        raw_hex="07E5",
        raw_int=2021,
        unit=None,
        transform=None,
    )

    assert trace.second_index is None
    assert trace.section == "header"
    assert trace.field_role == "record"
    assert trace.field_name == "year"
    assert trace.raw_hex == "07E5"
    assert trace.raw_int == 2021


def test_field_trace_can_be_created_for_second_level_field() -> None:
    trace = FieldTrace(
        record_index=0,
        second_index=0,
        section="second_data",
        field_name="bx",
        field_role="second",
        byte_offset=128,
        byte_length=2,
        raw_hex="000A",
        raw_int=10,
        unit="nT",
        transform="scale=0.1",
    )

    assert trace.second_index == 0
    assert trace.section == "second_data"
    assert trace.field_role == "second"
    assert trace.field_name == "bx"


def test_field_trace_is_frozen_dataclass() -> None:
    trace = FieldTrace(
        record_index=0,
        second_index=None,
        section="footer",
        field_name="flight_number",
        field_role="record",
        byte_offset=1000,
        byte_length=2,
        raw_hex="0001",
        raw_int=1,
        unit=None,
        transform=None,
    )

    with pytest.raises(FrozenInstanceError):
        trace.field_name = "year"  # type: ignore[misc]
