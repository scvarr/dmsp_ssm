from pathlib import Path

import pytest

from dmsp_ssm._internal.orchestration.collection_result_builder import build_raw_collection_result
from dmsp_ssm._internal.orchestration.file_parse_result import FileParseResult
from dmsp_ssm._internal.orchestration.raw_collection_result import (
    RawCollectionResult,
    assemble_raw_collection_result,
)

from dmsp_ssm._internal.source.data_source import SourceFile
from dmsp_ssm._internal.pipeline.field_trace import FieldTrace
from dmsp_ssm._internal.pipeline.raw_record import RawRecord
from dmsp_ssm._internal.validator.contracts import ValidationResult

pytestmark = pytest.mark.unit


def _build_file_result(
    *,
    path: str,
    chunks: list[bytes],
    status: str = "ok",
    outcome: str = "nonfatal",
    candidate_count: int | None = None,
) -> FileParseResult:
    report = ValidationResult(
        status=status,
        outcome=outcome,  # type: ignore[arg-type]
        validated_chunks=list(chunks),
        incidents=[],
        summary={
            "candidate_record_count": candidate_count
            if candidate_count is not None
            else len(chunks)
        },
    )
    records = [
        RawRecord(raw_bytes=chunk, header={}, blocks={}, footer={})
        for chunk in chunks
    ]
    return FileParseResult(
        source_file=SourceFile(path=Path(path), kind="dat"),
        records=records,
        field_traces=[],
        report=report,
    )


def _trace(
    *,
    record_index: int,
    field_name: str,
    second_index: int | None = None,
) -> FieldTrace:
    return FieldTrace(
        record_index=record_index,
        second_index=second_index,
        section="second_data" if second_index is not None else "header",
        field_name=field_name,
        field_role="second" if second_index is not None else "record",
        byte_offset=0,
        byte_length=4,
        raw_hex="00000000",
        raw_int=0,
        unit=None,
        transform=None,
    )


def test_assemble_raw_collection_result_combines_records_and_aggregated_report() -> None:
    first = _build_file_result(path="a.dat", chunks=[b"a1", b"a2"], candidate_count=3)
    second = _build_file_result(
        path="b.dat",
        chunks=[b"b1"],
        status="error",
        outcome="fatal",
        candidate_count=4,
    )

    result = assemble_raw_collection_result([first, second])

    assert isinstance(result, RawCollectionResult)
    assert [record.raw_bytes for record in result.records] == [b"a1", b"a2", b"b1"]
    assert result.field_traces == []
    assert result.report.status == "error"
    assert result.report.outcome == "fatal"
    assert result.report.summary == {
        "file_count": 2,
        "file_error_count": 1,
        "candidate_record_count": 7,
        "validated_record_count": 3,
    }


def test_build_raw_collection_result_in_memory_mode_uses_same_semantics() -> None:
    only = _build_file_result(path="single.dat", chunks=[b"x1"])

    result = build_raw_collection_result(
        file_results=[only],
    )

    assert isinstance(result, RawCollectionResult)
    assert [record.raw_bytes for record in result.records] == [b"x1"]
    assert result.field_traces == []
    assert result.report.summary == {
        "file_count": 1,
        "file_error_count": 0,
        "candidate_record_count": 1,
        "validated_record_count": 1,
    }


def test_assemble_raw_collection_result_renumbers_field_traces_to_global_indices() -> None:
    first = _build_file_result(path="a.dat", chunks=[b"a1"])
    first.field_traces = [
        _trace(record_index=0, field_name="year"),
        _trace(record_index=0, field_name="time", second_index=0),
    ]
    second = _build_file_result(path="b.dat", chunks=[b"b1"])
    second.field_traces = [
        _trace(record_index=0, field_name="year"),
        _trace(record_index=0, field_name="time", second_index=0),
    ]

    result = assemble_raw_collection_result([first, second])

    assert [record.raw_bytes for record in result.records] == [b"a1", b"b1"]
    assert [trace.record_index for trace in result.field_traces] == [0, 0, 1, 1]
    assert [trace.field_name for trace in result.field_traces] == [
        "year",
        "time",
        "year",
        "time",
    ]
