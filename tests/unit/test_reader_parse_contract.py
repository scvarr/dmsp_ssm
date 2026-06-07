from __future__ import annotations

import inspect
from pathlib import Path
from typing import get_type_hints

import pytest
import xarray as xr

from dmsp_ssm._internal.assembler.contracts import ArtifactBundle
from dmsp_ssm.parse_result import ParseResult
from dmsp_ssm._internal.pipeline.raw_record import RawRecord
from dmsp_ssm.reader import Reader
from dmsp_ssm._internal.validator.validator import Validator
from dmsp_ssm._internal.validator.contracts import ValidationResult

pytestmark = pytest.mark.unit


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


def test_reader_parse_signature_declares_ssm_parse_result_return_type() -> None:
    signature = inspect.signature(Reader.parse)
    resolved_hints = get_type_hints(Reader.parse)

    assert signature.return_annotation == "ParseResult"
    assert resolved_hints["return"] is ParseResult

    assert "options" in signature.parameters
    assert "recursive" in signature.parameters
    assert "error_policy" in signature.parameters
    assert "include_missing_minute_ranges" in signature.parameters


def test_reader_parse_does_not_construct_parse_result_directly() -> None:
    parse_source_code = inspect.getsource(Reader.parse)

    assert "ParseResult(" not in parse_source_code
    assert "run_reader_parse_use_case(" in parse_source_code


def test_reader_parse_returns_only_ssm_parse_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_validate(self: Validator, raw_bytes: bytes) -> object:
        assert raw_bytes == b"canonical-stream"
        return {"validated_chunks": [b"canonical-chunk"], "status": "ok"}

    class ParserStub:
        def parse_record(self, record: bytes) -> RawRecord:
            return _build_decode_compatible_raw_record(record)

    source_file = tmp_path / "canonical.dat"
    source_file.write_bytes(b"canonical-stream")

    monkeypatch.setattr(Validator, "validate", fake_validate)
    reader = Reader()
    reader._runtime.record_parser = ParserStub()  # type: ignore[assignment]

    result = reader.parse(source_file)

    assert isinstance(result, ParseResult)
    assert not isinstance(result, list)
    assert not isinstance(result, tuple)
    assert isinstance(result.records, xr.Dataset)
    assert set(result.records.dims) == {"record", "second"}
    assert set(result.records.data_vars) == {
        "valid",
        "time",
        "bx",
        "by",
        "bz",
        "flight_number",
        "year",
        "day_of_year",
        "minute_start_sec_of_day",
        "latitude_deg",
        "longitude_deg",
        "altitude_km",
    }
    assert not hasattr(result, "artifact")
    assert not hasattr(result, "decoded")


def test_reader_parse_adds_missing_minutes_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_validate(self: Validator, raw_bytes: bytes) -> object:
        return {"validated_chunks": [b"canonical-chunk"], "status": "ok", "summary": {}}

    class ParserStub:
        def parse_record(self, record: bytes) -> RawRecord:
            return _build_decode_compatible_raw_record(record)

    source_file = tmp_path / "canonical.dat"
    source_file.write_bytes(b"canonical-stream")

    monkeypatch.setattr(Validator, "validate", fake_validate)
    reader = Reader()
    reader._runtime.record_parser = ParserStub()  # type: ignore[assignment]

    result = reader.parse(source_file)
    summary = result.report["summary"] if isinstance(result.report, dict) else result.report.summary

    assert summary["expected_record_count"] == 1440
    assert summary["missing_record_count"] == 1439
    assert summary["has_missing_records"] is True
    assert "missing_minute_ranges" not in summary


def test_reader_parse_adds_missing_minute_ranges_only_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_validate(self: Validator, raw_bytes: bytes) -> object:
        return {"validated_chunks": [b"canonical-chunk"], "status": "ok", "summary": {}}

    class ParserStub:
        def parse_record(self, record: bytes) -> RawRecord:
            return _build_decode_compatible_raw_record(record)

    source_file = tmp_path / "canonical.dat"
    source_file.write_bytes(b"canonical-stream")

    monkeypatch.setattr(Validator, "validate", fake_validate)
    reader = Reader()
    reader._runtime.record_parser = ParserStub()  # type: ignore[assignment]

    result = reader.parse(source_file, include_missing_minute_ranges=True)
    summary = result.report["summary"] if isinstance(result.report, dict) else result.report.summary
    ranges = summary["missing_minute_ranges"]

    assert ranges == [
        {"start_minute": 1, "end_minute": 1439, "count": 1439},
    ]


def test_reader_parse_uses_internal_assembler_for_final_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_validate(self: Validator, raw_bytes: bytes) -> object:
        assert raw_bytes == b"canonical-stream"
        return {"validated_chunks": [b"canonical-chunk"], "status": "ok"}

    class ParserStub:
        def parse_record(self, record: bytes) -> RawRecord:
            return _build_decode_compatible_raw_record(record)

    class AssemblerSpy:
        def __init__(self) -> None:
            self.calls: list[ArtifactBundle] = []

        def assemble(self, bundle: ArtifactBundle) -> ParseResult:
            self.calls.append(bundle)
            return ParseResult(
                records=bundle.dataset,
                report=bundle.report,
                metadata={"assembled": True},
            )

    source_file = tmp_path / "canonical.dat"
    source_file.write_bytes(b"canonical-stream")

    monkeypatch.setattr(Validator, "validate", fake_validate)
    reader = Reader()
    reader._runtime.record_parser = ParserStub()  # type: ignore[assignment]
    assembler_spy = AssemblerSpy()
    reader._runtime.result_assembler = assembler_spy  # type: ignore[assignment]

    result = reader.parse(source_file)

    assert len(assembler_spy.calls) == 1
    bundle = assembler_spy.calls[0]
    assert isinstance(bundle, ArtifactBundle)
    assert isinstance(bundle.report, ValidationResult | dict)
    assert isinstance(bundle.dataset, xr.Dataset)
    assert bundle.raw_records is None
    assert bundle.decoded_records is None
    assert isinstance(result, ParseResult)
    assert isinstance(result.records, xr.Dataset)
    assert result.report is bundle.report
    assert result.metadata == {"assembled": True}
