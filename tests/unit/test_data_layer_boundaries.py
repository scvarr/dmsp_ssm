from __future__ import annotations

import pytest
import xarray as xr

from dmsp_ssm._internal.pipeline import DecodedRecord
from dmsp_ssm._internal.builder import XArrayBuilder
from dmsp_ssm.parse_result import ParseResult
from dmsp_ssm._internal.pipeline import RawRecord
from dmsp_ssm._internal.validator import ValidationResult

pytestmark = pytest.mark.unit

FROZEN_SECOND_LEVEL_VARS = {"time", "bx", "by", "bz", "valid"}
FROZEN_RECORD_LEVEL_VARS = {
    "flight_number",
    "year",
    "day_of_year",
    "minute_start_sec_of_day",
    "latitude_deg",
    "longitude_deg",
    "altitude_km",
}
FROZEN_DATA_VARS = FROZEN_SECOND_LEVEL_VARS | FROZEN_RECORD_LEVEL_VARS


def test_data_layer_chain_keeps_raw_record_as_intermediate_stage() -> None:
    raw_record = RawRecord(
        raw_bytes=b"\x01",
        header={"year": 2000},
        blocks={},
        footer={"flight_number": 10},
    )
    decoded_record = DecodedRecord(
        header={
            "year": 2000,
            "day_of_year": 100,
            "first_minute_first_second_time": 0,
            "geodetic_latitude": 9000,
            "geographic_longitude": 18000,
            "altitude_km": 400,
        },
        blocks={"second_data": [{"time": 0.0, "bx": 1.0, "by": 2.0, "bz": 3.0}]},
        footer={"flight_number": 10},
    )
    report = ValidationResult(status="ok", validated_chunks=[b"\x01"])
    dataset = XArrayBuilder().build([decoded_record])

    result = ParseResult(records=dataset, report=report)

    assert isinstance(raw_record, RawRecord)
    assert isinstance(result.records, xr.Dataset)
    assert result.records.sizes["record"] == 1
    assert set(result.records.data_vars) == FROZEN_DATA_VARS
    assert "geodetic_latitude" not in result.records.data_vars
    assert "geographic_longitude" not in result.records.data_vars
    assert not hasattr(result, "decoded")
    assert not hasattr(result, "dataset")


def test_data_layer_chain_defines_decoded_record_as_next_layer_after_raw_record() -> None:
    decoded = DecodedRecord(
        header={"year": 2001},
        blocks={},
        footer={"flight_number": 11},
    )

    assert decoded.header["year"] == 2001
    assert decoded.blocks == {}
    assert decoded.footer["flight_number"] == 11


def test_data_layer_chain_keeps_dataset_as_builder_layer_over_decoded_records() -> None:
    raw_record = RawRecord(
        raw_bytes=b"\x03",
        header={"year": 2002},
        blocks={},
        footer={"flight_number": 12},
    )
    decoded = DecodedRecord(
        header={
            "year": 2002,
            "day_of_year": 100,
            "first_minute_first_second_time": 0,
            "geodetic_latitude": 9000,
            "geographic_longitude": 18000,
            "altitude_km": 400,
        },
        blocks={"second_data": [{"time": 0.0, "bx": 1.0, "by": 2.0, "bz": 3.0}]},
        footer={"flight_number": 12},
    )
    report = ValidationResult(status="ok", validated_chunks=[b"\x03"])
    dataset = XArrayBuilder().build([decoded])

    result = ParseResult(
        records=dataset,
        report=report,
    )

    assert isinstance(raw_record, RawRecord)
    assert isinstance(result.records, xr.Dataset)
    assert result.records.sizes["record"] == 1
    assert result.report is report
    assert not hasattr(result, "decoded")
    assert not hasattr(result, "dataset")
