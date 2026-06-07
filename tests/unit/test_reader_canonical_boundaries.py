from __future__ import annotations

from pathlib import Path

import pytest
import xarray as xr

from dmsp_ssm._internal.source.data_source import (
    DataSource,
    SourceFile,
)
from dmsp_ssm.parse_result import ParseResult
from dmsp_ssm._internal.pipeline.raw_record import RawRecord
from dmsp_ssm.reader import Reader
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


def _build_decode_compatible_raw_record(record: bytes) -> RawRecord:
    return RawRecord(
        raw_bytes=record,
        header={
            "year": 2024,
            "day_of_year": 100,
            "first_minute_first_second_time": 12345,
            "geodetic_latitude": 9000,
            "geographic_longitude": 18000,
            "altitude_km": 400,
        },
        blocks={
            "second_data": [
                {
                    "time": 1000 + index,
                    "bx": 10 + index,
                    "by": 20 + index,
                    "bz": 30 + index,
                }
                for index in range(60)
            ]
        },
        footer={"flight_number": 10},
    )


def test_canonical_path_uses_internal_data_source_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_file = SourceFile(path=Path("input/canonical.dat"), kind="dat")
    events: list[str] = []

    def fake_list_source_files(self: DataSource) -> list[SourceFile]:
        events.append("list_source_files")
        return [source_file]

    def fake_read_source_file(
        self: DataSource,
        file_descriptor: SourceFile,
    ) -> bytes:
        assert file_descriptor == source_file
        events.append("read_source_file")
        return b"canonical-stream"

    def fake_validate(self: Validator, raw_bytes: bytes) -> object:
        assert raw_bytes == b"canonical-stream"
        events.append("validate")
        return {"validated_chunks": [b"canonical-chunk"], "status": "ok"}

    class ParserStub:
        def parse_record(self, record: bytes) -> RawRecord:
            assert record == b"canonical-chunk"
            events.append("parse")
            return _build_decode_compatible_raw_record(record)

    monkeypatch.setattr(DataSource, "list_source_files", fake_list_source_files)
    monkeypatch.setattr(DataSource, "read_source_file", fake_read_source_file)
    monkeypatch.setattr(Validator, "validate", fake_validate)

    reader = Reader()
    reader._runtime.record_parser = ParserStub()  # type: ignore[assignment]

    result = reader.parse("input")

    assert isinstance(result, ParseResult)
    assert isinstance(result.records, xr.Dataset)
    assert result.records.sizes["record"] == 1
    assert result.records.sizes["second"] == 60
    assert set(result.records.data_vars) == FROZEN_DATA_VARS
    assert "geodetic_latitude" not in result.records.data_vars
    assert "geographic_longitude" not in result.records.data_vars
    assert events == [
        "list_source_files",
        "read_source_file",
        "validate",
        "parse",
    ]
