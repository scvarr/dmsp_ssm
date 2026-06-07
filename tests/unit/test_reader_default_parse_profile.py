from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import xarray as xr
from pytest import MonkeyPatch

from dmsp_ssm._internal.format.definition import FormatDefinition
from dmsp_ssm.parse_options import ParseOptions
from dmsp_ssm.reader import Reader
from dmsp_ssm._internal.pipeline.raw_record import RawRecord
from dmsp_ssm._internal.validator.validator import Validator

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


def _build_decode_compatible_raw_record(record: bytes) -> RawRecord:
    return RawRecord(
        raw_bytes=record,
        header={
            "year": 2000,
            "day_of_year": 100,
            "first_minute_first_second_time": 0,
            "geodetic_latitude": 9000,
            "geographic_longitude": 18000,
            "altitude_km": 4000,
        },
        blocks={
            "second_data": [
                {"time": 0, "bx": 1, "by": 2, "bz": 3}
                for _ in range(60)
            ]
        },
        footer={"flight_number": 10},
    )


def _build_valid_record(
    format_definition: dict,
    *,
    year: int = 2000,
    day_of_year: int = 100,
    flight_number: int = 10,
) -> bytes:
    record = bytearray(format_definition["record_size"])

    field_definitions = {
        field["name"]: field
        for section in ("header", "footer")
        for field in format_definition.get(section, [])
    }
    values = {
        "year": year,
        "day_of_year": day_of_year,
        "flight_number": flight_number,
    }

    for field_name, value in values.items():
        field = field_definitions[field_name]
        start = field["offset"]
        end = start + field["size"]
        record[start:end] = value.to_bytes(
            field["size"],
            byteorder=format_definition["byte_order"],
            signed=True,
        )

    return bytes(record)


def test_parse_without_options_uses_non_strict_error_policy_by_default(
    tmp_path: Path,
) -> None:
    format_definition = FormatDefinition().as_dict()
    valid_record = _build_valid_record(format_definition)
    raw_stream = valid_record + b"tail"

    source_file = tmp_path / "input.dat"
    source_file.write_bytes(raw_stream)

    reader = Reader()
    result = reader.parse(source_file)

    assert result.report.status == "ok"
    assert result.report.outcome == "nonfatal"
    assert any(incident.kind == "trailing_bytes" for incident in result.report.incidents)


def test_parse_without_options_keeps_single_file_report_for_canonical_file_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "single.dat"
    source_file.write_bytes(b"raw-single")
    single_report = {
        "status": "ok",
        "outcome": "nonfatal",
        "validated_chunks": [b"single-chunk"],
        "incidents": [],
        "summary": {"candidate_record_count": 1},
    }

    def fake_validate(self: Validator, raw_bytes: bytes) -> object:
        assert raw_bytes == b"raw-single"
        return single_report

    class ParserStub:
        def parse_record(self, record: bytes) -> RawRecord:
            return _build_decode_compatible_raw_record(record)

    monkeypatch.setattr(Validator, "validate", fake_validate)
    reader = Reader()
    reader._runtime.record_parser = ParserStub()  # type: ignore[assignment]

    result = reader.parse(source_file)

    assert result.records.sizes["record"] == 1
    assert result.records.sizes["second"] == 60
    assert set(result.records.data_vars) == FROZEN_DATA_VARS
    assert "geodetic_latitude" not in result.records.data_vars
    assert "geographic_longitude" not in result.records.data_vars
    assert result.records["bx"].values[0, 0] == 1.0
    assert result.records["by"].values[0, 0] == 2.0
    assert result.records["bz"].values[0, 0] == 3.0
    assert result.report is single_report


def test_parse_without_options_aggregates_directory_results_for_multi_file_source(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "a.dat").write_bytes(b"raw-a")
    (input_dir / "b.dat").write_bytes(b"raw-b")

    def fake_validate(self: Validator, raw_bytes: bytes) -> object:
        if raw_bytes == b"raw-a":
            return {
                "status": "ok",
                "outcome": "nonfatal",
                "validated_chunks": [b"a1"],
                "incidents": [],
                "summary": {"candidate_record_count": 1},
            }
        return {
            "status": "error",
            "outcome": "fatal",
            "validated_chunks": [b"b1", b"b2"],
            "incidents": [],
            "summary": {"candidate_record_count": 3},
        }

    class ParserStub:
        def parse_record(self, record: bytes) -> RawRecord:
            return _build_decode_compatible_raw_record(record)

    monkeypatch.setattr(Validator, "validate", fake_validate)
    reader = Reader()
    reader._runtime.record_parser = ParserStub()  # type: ignore[assignment]

    result = reader.parse(input_dir)

    assert result.records.sizes["record"] == 3
    assert result.records.sizes["second"] == 60
    assert set(result.records.data_vars) == FROZEN_DATA_VARS
    assert "geodetic_latitude" not in result.records.data_vars
    assert "geographic_longitude" not in result.records.data_vars
    assert result.records["bx"].values[:, 0].tolist() == [1.0, 1.0, 1.0]
    assert result.report.summary["file_count"] == 2
    assert result.report.summary["file_error_count"] == 1
    assert result.report.summary["candidate_record_count"] == 4
    assert result.report.summary["validated_record_count"] == 3
    assert result.report.status == "error"
    assert result.report.outcome == "fatal"


def test_parse_public_table_output_profile_returns_long_format_rows(
    tmp_path: Path,
) -> None:
    format_definition = FormatDefinition().as_dict()
    source_file = tmp_path / "input.dat"
    source_file.write_bytes(_build_valid_record(format_definition))

    reader = Reader()
    result = reader.parse(source_file, options=ParseOptions(output_profile="table"))

    assert isinstance(result.records, list)
    assert result.records
    first_row = result.records[0]
    assert set(first_row) == TABLE_TRACE_REQUIRED_COLUMNS

    year_row = next(row for row in result.records if row["field_name"] == "year")
    assert year_row["second_index"] is None
    assert year_row["field_role"] == "record"
    assert year_row["raw_hex"] is not None
    assert year_row["raw_int"] is not None
    assert "decoded_value" in year_row
    assert "normalized_value" in year_row
    assert isinstance(year_row["valid"], bool)

    second_row = next(
        row
        for row in result.records
        if row["field_name"] in {"time", "bx"} and isinstance(row["second_index"], int)
    )
    assert second_row["field_role"] == "second"
    assert second_row["raw_hex"] is not None
    assert second_row["raw_int"] is not None
    assert "decoded_value" in second_row
    assert "normalized_value" in second_row
    assert isinstance(second_row["valid"], bool)


def test_parse_public_xarray_output_profile_keeps_current_runtime_path(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "single.dat"
    source_file.write_bytes(b"raw-single")

    def fake_validate(self: Validator, raw_bytes: bytes) -> object:
        assert raw_bytes == b"raw-single"
        return {
            "status": "ok",
            "outcome": "nonfatal",
            "validated_chunks": [b"single-chunk"],
            "incidents": [],
            "summary": {"candidate_record_count": 1},
        }

    class ParserStub:
        def parse_record(self, record: bytes) -> RawRecord:
            return _build_decode_compatible_raw_record(record)

    monkeypatch.setattr(Validator, "validate", fake_validate)
    reader = Reader()
    reader._runtime.record_parser = ParserStub()  # type: ignore[assignment]

    result = reader.parse(source_file, options=ParseOptions(output_profile="xarray"))

    assert isinstance(result.records, xr.Dataset)
    assert result.records.sizes["record"] == 1
    assert result.records.sizes["second"] == 60
    assert set(result.records.data_vars) == FROZEN_DATA_VARS


def test_parse_public_numpy_output_profile_returns_numpy_records_dict(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "single.dat"
    source_file.write_bytes(b"raw-single")

    def fake_validate(self: Validator, raw_bytes: bytes) -> object:
        assert raw_bytes == b"raw-single"
        return {
            "status": "ok",
            "outcome": "nonfatal",
            "validated_chunks": [b"single-chunk"],
            "incidents": [],
            "summary": {"candidate_record_count": 1},
        }

    class ParserStub:
        def parse_record(self, record: bytes) -> RawRecord:
            return _build_decode_compatible_raw_record(record)

    monkeypatch.setattr(Validator, "validate", fake_validate)
    reader = Reader()
    reader._runtime.record_parser = ParserStub()  # type: ignore[assignment]

    result = reader.parse(source_file, options=ParseOptions(output_profile="numpy"))

    assert isinstance(result.records, dict)
    assert set(result.records) == FROZEN_DATA_VARS
    assert all(isinstance(value, np.ndarray) for value in result.records.values())
    assert result.records["time"].shape == (1, 60)
    assert result.records["bx"].shape == (1, 60)
    assert result.records["by"].shape == (1, 60)
    assert result.records["bz"].shape == (1, 60)
    assert result.records["valid"].shape == (1, 60)
    assert result.records["flight_number"].shape == (1,)
    assert result.records["year"].shape == (1,)
    assert result.records["day_of_year"].shape == (1,)
    assert result.records["minute_start_sec_of_day"].shape == (1,)
    assert result.records["latitude_deg"].shape == (1,)
    assert result.records["longitude_deg"].shape == (1,)
    assert result.records["altitude_km"].shape == (1,)
    assert result.records["valid"].dtype == bool
    assert np.all(result.records["valid"])
