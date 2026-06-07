from pathlib import Path

import pytest

from dmsp_ssm._internal.orchestration.file_parse_result import FileParseResult
from dmsp_ssm._internal.orchestration.report_aggregation import aggregate_file_reports
from dmsp_ssm._internal.source.data_source import SourceFile
from dmsp_ssm._internal.pipeline.raw_record import RawRecord
from dmsp_ssm._internal.validator.contracts import (
    ValidationIncident,
    ValidationResult,
)

pytestmark = pytest.mark.unit


def _file_result(
    *,
    name: str,
    status: str,
    outcome: str,
    candidate_record_count: int,
    validated_chunks: list[bytes],
    incident_kinds: list[str],
) -> FileParseResult:
    incidents = [
        ValidationIncident(
            kind=kind,
            start_offset=0,
            end_offset=1,
            message=kind,
        )
        for kind in incident_kinds
    ]
    report = ValidationResult(
        status=status,
        outcome=outcome,  # type: ignore[arg-type]
        validated_chunks=validated_chunks,
        incidents=incidents,
        summary={"candidate_record_count": candidate_record_count},
    )
    return FileParseResult(
        source_file=SourceFile(path=Path(name), kind="dat"),
        records=[
            RawRecord(raw_bytes=chunk, header={}, blocks={}, footer={})
            for chunk in validated_chunks
        ],
        field_traces=[],
        report=report,
    )


def test_aggregate_file_reports_combines_status_outcome_incidents_and_summary() -> None:
    first = _file_result(
        name="a.dat",
        status="ok",
        outcome="nonfatal",
        candidate_record_count=5,
        validated_chunks=[b"a1", b"a2"],
        incident_kinds=["trailing_bytes"],
    )
    second = _file_result(
        name="b.dat",
        status="error",
        outcome="fatal",
        candidate_record_count=7,
        validated_chunks=[b"b1"],
        incident_kinds=["invalid_record", "desync"],
    )

    aggregated = aggregate_file_reports([first, second])

    assert aggregated.status == "error"
    assert aggregated.outcome == "fatal"
    assert [chunk for chunk in aggregated.validated_chunks] == [b"a1", b"a2", b"b1"]
    assert [incident.kind for incident in aggregated.incidents] == [
        "trailing_bytes",
        "invalid_record",
        "desync",
    ]
    assert aggregated.summary == {
        "file_count": 2,
        "file_error_count": 1,
        "candidate_record_count": 12,
        "validated_record_count": 3,
    }


def test_aggregate_file_reports_single_file_uses_same_semantics() -> None:
    only = _file_result(
        name="single.dat",
        status="ok",
        outcome="nonfatal",
        candidate_record_count=1,
        validated_chunks=[b"x1"],
        incident_kinds=[],
    )

    aggregated = aggregate_file_reports([only])

    assert aggregated.status == "ok"
    assert aggregated.outcome == "nonfatal"
    assert aggregated.summary == {
        "file_count": 1,
        "file_error_count": 0,
        "candidate_record_count": 1,
        "validated_record_count": 1,
    }


def test_aggregate_file_reports_returns_empty_totals_for_empty_collection() -> None:
    aggregated = aggregate_file_reports([])

    assert aggregated.status == "ok"
    assert aggregated.outcome == "nonfatal"
    assert aggregated.validated_chunks == []
    assert aggregated.incidents == []
    assert aggregated.summary == {
        "file_count": 0,
        "file_error_count": 0,
        "candidate_record_count": 0,
        "validated_record_count": 0,
    }
