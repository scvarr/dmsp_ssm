from __future__ import annotations

from pathlib import Path

import pytest
import xarray as xr

from dmsp_ssm._internal.source.data_source import (
    DataSource,
    SourceFile,
)
from dmsp_ssm._internal.format.definition import FormatDefinition
from dmsp_ssm.parse_options import ParseOptions
from dmsp_ssm.parse_result import ParseResult
from dmsp_ssm._internal.pipeline.raw_record import RawRecord
from dmsp_ssm.reader import Reader
from dmsp_ssm._internal.validator.contracts import ValidationResult
from dmsp_ssm._internal.validator.policy import ValidationErrorPolicy
from dmsp_ssm._internal.validator.validator import Validator

pytestmark = pytest.mark.integration

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


def test_ssm_reader_uses_internal_data_source_constructor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    source_file = SourceFile(path=Path("input.dat"), kind="dat")

    def fake_init(self: DataSource, path: Path | str, *, recursive: bool = False) -> None:
        captured["path"] = path
        captured["recursive"] = recursive
        self.path = Path(path)
        self.recursive = recursive

    def fake_list_source_files(self: DataSource) -> list[SourceFile]:
        return [source_file]

    def fake_read_source_file(
        self: DataSource,
        file_descriptor: SourceFile,
    ) -> bytes:
        assert file_descriptor == source_file
        return b""

    monkeypatch.setattr(DataSource, "__init__", fake_init)
    monkeypatch.setattr(DataSource, "list_source_files", fake_list_source_files)
    monkeypatch.setattr(DataSource, "read_source_file", fake_read_source_file)

    reader = Reader()
    result = reader.parse("test.dat")

    assert isinstance(result, ParseResult)
    assert captured == {"path": "test.dat", "recursive": True}


def test_ssm_reader_parse_sugar_overrides_recursive_in_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    source_file = SourceFile(path=Path("input.dat"), kind="dat")

    def fake_init(self: DataSource, path: Path | str, *, recursive: bool = False) -> None:
        captured["path"] = path
        captured["recursive"] = recursive
        self.path = Path(path)
        self.recursive = recursive

    def fake_list_source_files(self: DataSource) -> list[SourceFile]:
        return [source_file]

    def fake_read_source_file(
        self: DataSource,
        file_descriptor: SourceFile,
    ) -> bytes:
        assert file_descriptor == source_file
        return b""

    monkeypatch.setattr(DataSource, "__init__", fake_init)
    monkeypatch.setattr(DataSource, "list_source_files", fake_list_source_files)
    monkeypatch.setattr(DataSource, "read_source_file", fake_read_source_file)

    reader = Reader()
    result = reader.parse(
        "test.dat",
        options=ParseOptions(recursive=True),
        recursive=False,
    )

    assert isinstance(result, ParseResult)
    assert captured == {"path": "test.dat", "recursive": False}


def test_ssm_reader_uses_canonical_source_file_pipeline_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    source_file = SourceFile(path=Path("input.dat"), kind="dat")

    def fake_list_source_files(self: DataSource) -> list[SourceFile]:
        events.append("list_source_files")
        return [source_file]

    def fake_read_source_file(
        self: DataSource,
        file_descriptor: SourceFile,
    ) -> bytes:
        assert file_descriptor == source_file
        events.append("read_source_file")
        return b"raw-stream"

    def fake_validate(self: Validator, raw_bytes: bytes) -> object:
        events.append(f"validate:{raw_bytes!r}")
        return {"validated_chunks": [b"chunk-1", b"chunk-2"]}

    class ParserSpy:
        def parse_record(self, record: bytes) -> RawRecord:
            events.append(f"parse:{record!r}")
            return _build_decode_compatible_raw_record(record)

    monkeypatch.setattr(DataSource, "list_source_files", fake_list_source_files)
    monkeypatch.setattr(DataSource, "read_source_file", fake_read_source_file)
    monkeypatch.setattr(Validator, "validate", fake_validate)

    reader = Reader()
    reader._runtime.record_parser = ParserSpy()  # type: ignore[assignment]
    result = reader.parse("input.dat")

    assert events == [
        "list_source_files",
        "read_source_file",
        "validate:b'raw-stream'",
        "parse:b'chunk-1'",
        "parse:b'chunk-2'",
    ]
    assert isinstance(result.records, xr.Dataset)
    assert result.records.sizes["record"] == 2
    assert result.records.sizes["second"] == 60
    assert set(result.records.data_vars) == FROZEN_DATA_VARS
    assert "geodetic_latitude" not in result.records.data_vars
    assert "geographic_longitude" not in result.records.data_vars
    assert result.records["time"].attrs["units"] == "s"
    assert result.records["bx"].attrs["units"] == "nT"
    assert result.records["latitude_deg"].attrs["units"] == "degree"
    assert result.records["altitude_km"].attrs["units"] == "km"


def test_ssm_reader_returns_report_as_primary_channel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_file = SourceFile(path=Path("input.dat"), kind="dat")
    report = {
        "status": "ok",
        "outcome": "nonfatal",
        "validated_chunks": [b"chunk"],
        "incidents": [],
        "summary": {"candidate_record_count": 1},
    }

    def fake_list_source_files(self: DataSource) -> list[SourceFile]:
        return [source_file]

    def fake_read_source_file(
        self: DataSource,
        file_descriptor: SourceFile,
    ) -> bytes:
        assert file_descriptor == source_file
        return b"raw-stream"

    def fake_validate(self: Validator, raw_bytes: bytes) -> object:
        assert raw_bytes == b"raw-stream"
        return report

    class ParserStub:
        def parse_record(self, record: bytes) -> RawRecord:
            return _build_decode_compatible_raw_record(record)

    monkeypatch.setattr(DataSource, "list_source_files", fake_list_source_files)
    monkeypatch.setattr(DataSource, "read_source_file", fake_read_source_file)
    monkeypatch.setattr(Validator, "validate", fake_validate)

    reader = Reader()
    reader._runtime.record_parser = ParserStub()  # type: ignore[assignment]
    result = reader.parse("input.dat")

    assert result.report is report
    assert isinstance(result.records, xr.Dataset)
    assert result.records.sizes["record"] == 1
    assert set(result.records.data_vars) == FROZEN_DATA_VARS
    assert "geodetic_latitude" not in result.records.data_vars
    assert "geographic_longitude" not in result.records.data_vars


def test_ssm_reader_uses_ssm_validator_by_default(tmp_path: Path) -> None:
    source_file = tmp_path / "input.dat"
    source_file.write_bytes(b"")

    reader = Reader()
    result = reader.parse(source_file)

    assert isinstance(reader._runtime.validator, Validator)
    assert isinstance(result.report, ValidationResult)


def test_ssm_reader_parse_applies_error_policy_from_options_to_default_validator(
    tmp_path: Path,
) -> None:
    format_definition = FormatDefinition().as_dict()
    valid_record = _build_valid_record(format_definition)
    raw_stream = valid_record + b"tail"
    source_file = tmp_path / "input.dat"
    source_file.write_bytes(raw_stream)

    reader = Reader()
    strict_result = reader.parse(
        source_file,
        options=ParseOptions(error_policy=ValidationErrorPolicy.STRICT),
    )
    resync_result = reader.parse(
        source_file,
        options=ParseOptions(error_policy=ValidationErrorPolicy.RESYNC),
    )

    assert strict_result.report.status == "error"
    assert strict_result.report.outcome == "fatal"
    assert resync_result.report.status == "ok"
    assert resync_result.report.outcome == "nonfatal"


def test_ssm_reader_parse_accepts_error_policy_sugar(
    tmp_path: Path,
) -> None:
    format_definition = FormatDefinition().as_dict()
    valid_record = _build_valid_record(format_definition)
    raw_stream = valid_record + b"tail"
    source_file = tmp_path / "input.dat"
    source_file.write_bytes(raw_stream)

    reader = Reader()
    result = reader.parse(
        source_file,
        error_policy=ValidationErrorPolicy.STRICT,
    )

    assert result.report.status == "error"
    assert result.report.outcome == "fatal"


def test_ssm_reader_parse_accepts_recursive_sugar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    source_file = SourceFile(path=Path("input.dat"), kind="dat")

    def fake_init(self: DataSource, path: Path | str, *, recursive: bool = False) -> None:
        captured["path"] = path
        captured["recursive"] = recursive
        self.path = Path(path)
        self.recursive = recursive

    def fake_list_source_files(self: DataSource) -> list[SourceFile]:
        return [source_file]

    def fake_read_source_file(
        self: DataSource,
        file_descriptor: SourceFile,
    ) -> bytes:
        assert file_descriptor == source_file
        return b""

    monkeypatch.setattr(DataSource, "__init__", fake_init)
    monkeypatch.setattr(DataSource, "list_source_files", fake_list_source_files)
    monkeypatch.setattr(DataSource, "read_source_file", fake_read_source_file)

    reader = Reader()
    result = reader.parse("input.dat", recursive=False)

    assert isinstance(result, ParseResult)
    assert captured == {"path": "input.dat", "recursive": False}


def test_ssm_reader_parse_rejects_invalid_options_type() -> None:
    reader = Reader()
    with pytest.raises(TypeError, match="ParseOptions"):
        reader.parse("input.dat", options=object())  # type: ignore[arg-type]


def test_ssm_reader_parse_sugar_error_policy_overrides_options(
    tmp_path: Path,
) -> None:
    format_definition = FormatDefinition().as_dict()
    valid_record = _build_valid_record(format_definition)
    raw_stream = valid_record + b"tail"
    source_file = tmp_path / "input.dat"
    source_file.write_bytes(raw_stream)

    reader = Reader()
    result = reader.parse(
        source_file,
        options=ParseOptions(error_policy=ValidationErrorPolicy.RESYNC),
        error_policy=ValidationErrorPolicy.STRICT,
    )

    assert result.report.status == "error"
    assert result.report.outcome == "fatal"


def test_ssm_reader_parse_rejects_incompatible_validator_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_file = SourceFile(path=Path("input.dat"), kind="dat")

    def fake_list_source_files(self: DataSource) -> list[SourceFile]:
        return [source_file]

    def fake_read_source_file(
        self: DataSource,
        file_descriptor: SourceFile,
    ) -> bytes:
        assert file_descriptor == source_file
        return b"raw-stream"

    def fake_validate(self: Validator, raw_bytes: bytes) -> object:
        return {"status": "ok"}

    monkeypatch.setattr(DataSource, "list_source_files", fake_list_source_files)
    monkeypatch.setattr(DataSource, "read_source_file", fake_read_source_file)
    monkeypatch.setattr(Validator, "validate", fake_validate)

    reader = Reader()
    with pytest.raises(ValueError, match="validated_chunks"):
        reader.parse("input.dat")


def test_reader_parse_uses_per_file_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_file = SourceFile(path=Path("input/canonical.dat"), kind="dat")
    report = {
        "status": "ok",
        "outcome": "nonfatal",
        "validated_chunks": [b"canonical-chunk"],
        "incidents": [],
        "summary": {"candidate_record_count": 1},
    }

    def fake_list_source_files(self: DataSource) -> list[SourceFile]:
        return [source_file]

    def fake_read_source_file(
        self: DataSource,
        file_descriptor: SourceFile,
    ) -> bytes:
        assert file_descriptor == source_file
        return b"raw-canonical"

    def fake_validate(self: Validator, raw_bytes: bytes) -> object:
        assert raw_bytes == b"raw-canonical"
        return report

    class ParserStub:
        def parse_record(self, record: bytes) -> RawRecord:
            return _build_decode_compatible_raw_record(record)

    monkeypatch.setattr(DataSource, "list_source_files", fake_list_source_files)
    monkeypatch.setattr(DataSource, "read_source_file", fake_read_source_file)
    monkeypatch.setattr(Validator, "validate", fake_validate)

    reader = Reader()
    reader._runtime.record_parser = ParserStub()  # type: ignore[assignment]
    result = reader.parse("input")

    assert isinstance(result.records, xr.Dataset)
    assert result.records.sizes["record"] == 1
    assert set(result.records.data_vars) == FROZEN_DATA_VARS
    assert "geodetic_latitude" not in result.records.data_vars
    assert "geographic_longitude" not in result.records.data_vars
    assert result.report is report


def test_reader_parse_adds_pre_parse_size_warning_diagnostic_when_threshold_exceeded(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    file_a = tmp_path / "a.dat"
    file_b = tmp_path / "b.dat"
    file_a.write_bytes(b"A" * 64)
    file_b.write_bytes(b"B" * 64)

    source_files = [
        SourceFile(path=file_a, kind="dat"),
        SourceFile(path=file_b, kind="dat"),
    ]

    def fake_list_source_files(self: DataSource) -> list[SourceFile]:
        return source_files

    def fake_read_source_file(
        self: DataSource,
        file_descriptor: SourceFile,
    ) -> bytes:
        with file_descriptor.path.open("rb") as stream:
            return stream.read()

    def fake_validate(self: Validator, raw_bytes: bytes) -> object:
        return {
            "status": "ok",
            "outcome": "nonfatal",
            "validated_chunks": [],
            "incidents": [],
            "summary": {"candidate_record_count": 0},
        }

    monkeypatch.setattr(DataSource, "list_source_files", fake_list_source_files)
    monkeypatch.setattr(DataSource, "read_source_file", fake_read_source_file)
    monkeypatch.setattr(Validator, "validate", fake_validate)

    reader = Reader(pre_parse_size_warning_threshold_bytes=1)
    result = reader.parse(str(tmp_path))

    assert result.report.summary["file_count"] == 2
    diagnostic = result.report.summary["pre_parse_input_estimate"]
    assert diagnostic["kind"] == "pre_parse_input_size_warning"
    assert diagnostic["threshold_bytes"] == 1
    assert diagnostic["total_input_bytes"] == 128
    assert diagnostic["estimated_record_count"] == 0
