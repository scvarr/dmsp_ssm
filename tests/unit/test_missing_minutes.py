from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from dmsp_ssm._internal.orchestration.file_parse_result import FileParseResult
from dmsp_ssm._internal.orchestration.missing_minutes import (
    inject_missing_minutes_summary,
)
from dmsp_ssm._internal.pipeline import RawRecord
from dmsp_ssm._internal.source import SourceFile

pytestmark = pytest.mark.unit


def _decoded_record_with_second(second_of_day: int) -> SimpleNamespace:
    return SimpleNamespace(
        header={"first_minute_first_second_time": second_of_day},
    )


def _raw_record_with_minute(minute_index: int) -> RawRecord:
    return RawRecord(
        raw_bytes=b"",
        header={"first_minute_first_second_time": minute_index * 60000},
        blocks={},
        footer={},
    )


def _file_result(file_name: str, minute_indices: range) -> FileParseResult:
    return FileParseResult(
        source_file=SourceFile(path=Path(file_name), kind="dat"),
        records=[_raw_record_with_minute(minute) for minute in minute_indices],
        field_traces=[],
        report={"status": "ok", "summary": {}},
    )


def test_missing_minutes_keeps_top_level_ranges_for_single_file() -> None:
    report = {"summary": {}}

    inject_missing_minutes_summary(
        report=report,
        records=[_decoded_record_with_second(0)],
        include_missing_minute_ranges=True,
        file_results=[_file_result("single.dat", range(1))],
    )

    assert report["summary"]["missing_minute_ranges"] == [
        {"start_minute": 1, "end_minute": 1439, "count": 1439},
    ]
    assert "missing_minute_ranges_by_file" not in report["summary"]


def test_missing_minutes_adds_per_file_ranges_for_directory() -> None:
    report = {"summary": {"file_count": 2}}
    records = [_decoded_record_with_second(minute * 60) for minute in range(1440)]
    file_results = [
        _file_result("a.dat", range(0, 720)),
        _file_result("b.dat", range(720, 1440)),
    ]

    inject_missing_minutes_summary(
        report=report,
        records=records,
        include_missing_minute_ranges=True,
        file_results=file_results,
    )

    summary = report["summary"]
    assert summary["missing_minute_ranges"] == []
    assert summary["missing_record_count"] == 1440
    assert summary["missing_minute_ranges_by_file"] == [
        {
            "source_file": "a.dat",
            "expected_record_count": 1440,
            "observed_record_count": 720,
            "missing_record_count": 720,
            "has_missing_records": True,
            "first_minute_index": 0,
            "last_minute_index": 719,
            "gap_count": 0,
            "missing_minute_ranges": [
                {"start_minute": 720, "end_minute": 1439, "count": 720},
            ],
        },
        {
            "source_file": "b.dat",
            "expected_record_count": 1440,
            "observed_record_count": 720,
            "missing_record_count": 720,
            "has_missing_records": True,
            "first_minute_index": 720,
            "last_minute_index": 1439,
            "gap_count": 0,
            "missing_minute_ranges": [
                {"start_minute": 0, "end_minute": 719, "count": 720},
            ],
        },
    ]


def test_missing_minutes_does_not_add_ranges_when_disabled() -> None:
    report = {"summary": {"file_count": 2}}

    inject_missing_minutes_summary(
        report=report,
        records=[_decoded_record_with_second(0)],
        include_missing_minute_ranges=False,
        file_results=[
            _file_result("a.dat", range(1)),
            _file_result("b.dat", range(1)),
        ],
    )

    assert "missing_minute_ranges" not in report["summary"]
    assert "missing_minute_ranges_by_file" not in report["summary"]
