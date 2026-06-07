from pathlib import Path

import pytest

from dmsp_ssm._internal.orchestration.collection_error_policy import CollectionErrorPolicy
from dmsp_ssm._internal.orchestration.collection_result_builder import build_raw_collection_result
from dmsp_ssm._internal.orchestration.file_parse_result import FileParseResult
from dmsp_ssm._internal.orchestration.file_pipeline import (
    iter_file_parse_results,
    map_source_files_to_results,
)
from dmsp_ssm._internal.source.data_source import SourceFile
from dmsp_ssm._internal.orchestration.raw_collection_result import RawCollectionResult
from dmsp_ssm._internal.format.definition import FormatDefinition
from dmsp_ssm._internal.pipeline.raw_record import RawRecord

pytestmark = pytest.mark.unit


def _build_record_chunk(seed: bytes) -> bytes:
    definition = FormatDefinition().as_dict()
    record_size = int(definition["record_size"])
    chunk = bytearray(record_size)
    chunk[: min(len(seed), record_size)] = seed[:record_size]
    return bytes(chunk)


def _make_file_result(path: str, chunk: bytes) -> FileParseResult:
    return FileParseResult(
        source_file=SourceFile(path=Path(path), kind="dat"),
        records=[RawRecord(raw_bytes=chunk, header={}, blocks={}, footer={})],
        field_traces=[],
        report={
            "status": "ok",
            "outcome": "nonfatal",
            "validated_chunks": [chunk],
            "incidents": [],
            "summary": {"candidate_record_count": 1},
        },
    )


def test_build_parse_result_in_memory_mode_returns_raw_collection_result() -> None:
    file_results = [_make_file_result("a.dat", b"a1"), _make_file_result("b.dat", b"b1")]

    result = build_raw_collection_result(
        file_results=file_results,
    )

    assert isinstance(result, RawCollectionResult)
    assert [record.raw_bytes for record in result.records] == [b"a1", b"b1"]
    assert result.report.summary["file_count"] == 2


def test_iter_file_parse_results_yields_file_level_results_in_order() -> None:
    source_files = [
        SourceFile(path=Path("a.dat"), kind="dat"),
        SourceFile(path=Path("b.dat"), kind="dat"),
    ]

    class StubDataSource:
        def read_source_file(self, source_file: SourceFile) -> bytes:
            return source_file.path.name.encode("ascii")

    class ValidatorStub:
        def validate(self, raw_bytes: bytes) -> object:
            return {"validated_chunks": [_build_record_chunk(raw_bytes)]}

    class ParserStub:
        def parse_record(self, record: bytes) -> RawRecord:
            return RawRecord(raw_bytes=record, header={}, blocks={}, footer={})

    results = list(
        iter_file_parse_results(
            data_source=StubDataSource(),
            source_files=source_files,
            validate_raw_bytes=ValidatorStub().validate,
            parse_record=ParserStub().parse_record,
            extract_validated_chunks=lambda *, validation_report: validation_report[
                "validated_chunks"
            ],
            format_definition=FormatDefinition(),
            policy=CollectionErrorPolicy.FAIL_FAST,
        )
    )

    assert [result.source_file.path.name for result in results] == ["a.dat", "b.dat"]
    assert [[record.raw_bytes for record in result.records] for result in results] == [
        [_build_record_chunk(b"a.dat")],
        [_build_record_chunk(b"b.dat")],
    ]
    assert all(result.field_traces for result in results)
    assert all(
        any(trace.field_name == "year" for trace in result.field_traces)
        for result in results
    )
    assert all(
        any(trace.field_name == "time" for trace in result.field_traces)
        for result in results
    )
    assert all(all(trace.record_index == 0 for trace in result.field_traces) for result in results)


def test_iter_file_parse_results_supports_skip_failed_file_policy() -> None:
    source_files = [
        SourceFile(path=Path("ok.dat"), kind="dat"),
        SourceFile(path=Path("bad.dat"), kind="dat"),
    ]

    class StubDataSource:
        def read_source_file(self, source_file: SourceFile) -> bytes:
            return source_file.path.name.encode("ascii")

    class ValidatorStub:
        def validate(self, raw_bytes: bytes) -> object:
            if raw_bytes == b"bad.dat":
                raise RuntimeError("bad file")
            return {"validated_chunks": [_build_record_chunk(raw_bytes)]}

    class ParserStub:
        def parse_record(self, record: bytes) -> RawRecord:
            return RawRecord(raw_bytes=record, header={}, blocks={}, footer={})

    results = list(
        iter_file_parse_results(
            data_source=StubDataSource(),
            source_files=source_files,
            validate_raw_bytes=ValidatorStub().validate,
            parse_record=ParserStub().parse_record,
            extract_validated_chunks=lambda *, validation_report: validation_report[
                "validated_chunks"
            ],
            format_definition=FormatDefinition(),
            policy=CollectionErrorPolicy.SKIP_FAILED_FILE,
        )
    )

    assert len(results) == 1
    assert results[0].source_file.path.name == "ok.dat"


def test_map_source_files_to_results_keeps_order() -> None:
    source_files = [
        SourceFile(path=Path("a.dat"), kind="dat"),
        SourceFile(path=Path("b.dat"), kind="dat"),
    ]

    class StubDataSource:
        def read_source_file(self, source_file: SourceFile) -> bytes:
            return source_file.path.name.encode("ascii")

    class ValidatorStub:
        def validate(self, raw_bytes: bytes) -> object:
            return {"validated_chunks": [_build_record_chunk(raw_bytes)]}

    class ParserStub:
        def parse_record(self, record: bytes) -> RawRecord:
            return RawRecord(raw_bytes=record, header={}, blocks={}, footer={})

    results = map_source_files_to_results(
        data_source=StubDataSource(),
        source_files=source_files,
        validate_raw_bytes=ValidatorStub().validate,
        parse_record=ParserStub().parse_record,
        extract_validated_chunks=lambda *, validation_report: validation_report[
            "validated_chunks"
        ],
        format_definition=FormatDefinition(),
        policy=CollectionErrorPolicy.FAIL_FAST,
    )

    assert [r.source_file.path.name for r in results] == ["a.dat", "b.dat"]
    assert results[0].field_traces
    assert all(trace.record_index == 0 for trace in results[0].field_traces)


def test_iter_file_parse_results_assigns_file_local_record_indices_for_multiple_chunks() -> None:
    source_files = [SourceFile(path=Path("multi.dat"), kind="dat")]

    class StubDataSource:
        def read_source_file(self, source_file: SourceFile) -> bytes:
            return source_file.path.name.encode("ascii")

    class ValidatorStub:
        def validate(self, raw_bytes: bytes) -> object:
            return {
                "validated_chunks": [
                    _build_record_chunk(raw_bytes + b":0"),
                    _build_record_chunk(raw_bytes + b":1"),
                ]
            }

    class ParserStub:
        def parse_record(self, record: bytes) -> RawRecord:
            return RawRecord(raw_bytes=record, header={}, blocks={}, footer={})

    results = list(
        iter_file_parse_results(
            data_source=StubDataSource(),
            source_files=source_files,
            validate_raw_bytes=ValidatorStub().validate,
            parse_record=ParserStub().parse_record,
            extract_validated_chunks=lambda *, validation_report: validation_report[
                "validated_chunks"
            ],
            format_definition=FormatDefinition(),
            policy=CollectionErrorPolicy.FAIL_FAST,
        )
    )

    assert len(results) == 1
    assert [record.raw_bytes for record in results[0].records] == [
        _build_record_chunk(b"multi.dat:0"),
        _build_record_chunk(b"multi.dat:1"),
    ]

    trace_record_indices = [trace.record_index for trace in results[0].field_traces]
    assert 0 in trace_record_indices
    assert 1 in trace_record_indices
    first_record_one_position = trace_record_indices.index(1)
    assert all(index == 0 for index in trace_record_indices[:first_record_one_position])
