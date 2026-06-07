from pathlib import Path

import pytest

from dmsp_ssm._internal.orchestration.collection_error_policy import CollectionErrorPolicy
from dmsp_ssm._internal.orchestration.collection_result_builder import build_raw_collection_result
from dmsp_ssm._internal.orchestration.file_parse_result import FileParseResult
from dmsp_ssm._internal.orchestration.file_pipeline import (
    UNKNOWN_FLIGHT_NUMBER,
    iter_file_parse_results,
    map_source_files_to_results,
    parse_source_file,
    _normalize_record_flight_number,
)
from dmsp_ssm._internal.source.data_source import SourceFile
from dmsp_ssm._internal.orchestration.raw_collection_result import RawCollectionResult
from dmsp_ssm._internal.format.definition import FormatDefinition
from dmsp_ssm._internal.pipeline.record_parser import RecordParser
from dmsp_ssm._internal.pipeline.raw_record import RawRecord
from dmsp_ssm._internal.validator.validation_report_adapter import extract_validated_chunks
from dmsp_ssm._internal.validator.validator import Validator
from dmsp_ssm._internal.decoder.decoder import Decoder
from dmsp_ssm._internal.builder.table_builder import TableBuilder

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


@pytest.mark.parametrize("flight_number", [0, 14, 20])
def test_normalize_record_flight_number_keeps_valid_binary_value(
    flight_number: int,
) -> None:
    record = RawRecord(
        raw_bytes=b"",
        header={},
        blocks={},
        footer={"flight_number": flight_number},
    )

    result = _normalize_record_flight_number(
        record=record,
        source_file=SourceFile(path=Path("m1295001.dat.gz"), kind="gz"),
    )

    assert result.footer["flight_number"] == flight_number


@pytest.mark.parametrize(
    ("source_name", "raw_flight_number", "expected_flight_number"),
    [
        ("m1295001.dat.gz", 3545, 12),
        ("m1405121.dat.gz", 5548, 14),
    ],
)
def test_normalize_record_flight_number_uses_source_file_name_for_legacy_values(
    source_name: str,
    raw_flight_number: int,
    expected_flight_number: int,
) -> None:
    record = RawRecord(
        raw_bytes=b"",
        header={},
        blocks={},
        footer={"flight_number": raw_flight_number},
    )

    result = _normalize_record_flight_number(
        record=record,
        source_file=SourceFile(path=Path(source_name), kind="gz"),
    )

    assert result.footer["flight_number"] == expected_flight_number


def test_normalize_record_flight_number_uses_sentinel_for_unknown_source_name() -> None:
    record = RawRecord(
        raw_bytes=b"",
        header={},
        blocks={},
        footer={"flight_number": 5548},
    )

    result = _normalize_record_flight_number(
        record=record,
        source_file=SourceFile(path=Path("unknown.dat.gz"), kind="gz"),
    )

    assert result.footer["flight_number"] == UNKNOWN_FLIGHT_NUMBER


def test_table_trace_keeps_raw_flight_number_and_uses_normalized_value() -> None:
    definition = FormatDefinition().as_dict()
    record = bytearray(definition["record_size"])
    record[0:4] = (2005).to_bytes(4, byteorder="big", signed=True)
    record[4:8] = (121).to_bytes(4, byteorder="big", signed=True)
    record[984:988] = (5548).to_bytes(4, byteorder="big", signed=True)

    class StubDataSource:
        def read_source_file(self, source_file: SourceFile) -> bytes:
            return bytes(record)

    file_result = parse_source_file(
        data_source=StubDataSource(),
        source_file=SourceFile(path=Path("m1405121.dat.gz"), kind="gz"),
        validate_raw_bytes=Validator(format_definition=definition).validate,
        parse_record=RecordParser(format_definition=definition).parse_record,
        extract_validated_chunks=extract_validated_chunks,
        format_definition=FormatDefinition(),
    )
    decoded_records = [
        Decoder(format_definition=definition).decode(record)
        for record in file_result.records
    ]

    rows = TableBuilder().build(
        field_traces=file_result.field_traces,
        decoded_records=decoded_records,
    )

    flight_row = next(row for row in rows if row["field_name"] == "flight_number")
    assert flight_row["raw_int"] == 5548
    assert flight_row["decoded_value"] == 14
    assert flight_row["normalized_value"] == 14
