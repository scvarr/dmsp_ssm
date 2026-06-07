from __future__ import annotations

from pathlib import Path

import pytest

from dmsp_ssm.reader import Reader
from dmsp_ssm._internal.pipeline import RawRecord
from dmsp_ssm._internal.validator import Validator

pytestmark = pytest.mark.unit


def _build_decode_compatible_raw_record(record: bytes) -> RawRecord:
    year = 2001 if record == b"A1" else 2002
    day_of_year = 101 if record == b"A1" else 102
    flight_number = 11 if record == b"A1" else 12
    bx = 101 if record == b"A1" else 202
    return RawRecord(
        raw_bytes=record,
        header={
            "year": year,
            "day_of_year": day_of_year,
            "first_minute_first_second_time": 0,
            "geodetic_latitude": 9000,
            "geographic_longitude": 18000,
            "altitude_km": 4000,
        },
        blocks={
            "second_data": [
                {"time": 0, "bx": bx, "by": 2, "bz": 3}
                for _ in range(60)
            ]
        },
        footer={"flight_number": flight_number},
    )


def test_reader_parse_is_deterministic_for_multi_file_records_and_report_order(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "a.dat").write_bytes(b"A")
    (input_dir / "b.dat").write_bytes(b"B")

    def fake_validate(self: Validator, raw_bytes: bytes) -> object:
        if raw_bytes == b"A":
            return {
                "status": "ok",
                "outcome": "nonfatal",
                "validated_chunks": [b"A1"],
                "incidents": ["inc-A"],
                "summary": {"candidate_record_count": 1},
            }
        return {
            "status": "error",
            "outcome": "fatal",
            "validated_chunks": [b"B1"],
            "incidents": ["inc-B"],
            "summary": {"candidate_record_count": 1},
        }

    class ParserStub:
        def parse_record(self, record: bytes) -> RawRecord:
            return _build_decode_compatible_raw_record(record)

    monkeypatch.setattr(Validator, "validate", fake_validate)
    reader = Reader()
    reader._runtime.record_parser = ParserStub()  # type: ignore[assignment]

    first = reader.parse(input_dir)
    second = reader.parse(input_dir)

    assert first.records["bx"].values[:, 0].tolist() == [101.0, 202.0]
    assert second.records["bx"].values[:, 0].tolist() == [101.0, 202.0]
    assert first.records.sizes["record"] == 2
    assert second.records.sizes["record"] == 2
    assert first.report.validated_chunks == []
    assert second.report.validated_chunks == []
    assert first.report.incidents == ["inc-A", "inc-B"]
    assert second.report.incidents == ["inc-A", "inc-B"]
    assert first.report.summary["file_count"] == 2
    assert first.report.summary["file_error_count"] == 1
    assert first.report.summary["candidate_record_count"] == 2
    assert first.report.summary["validated_record_count"] == 2
    assert second.report.summary == first.report.summary
