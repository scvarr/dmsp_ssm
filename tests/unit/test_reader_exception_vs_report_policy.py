from __future__ import annotations

from pathlib import Path

import pytest

from dmsp_ssm._internal.format.definition import FormatDefinition
from dmsp_ssm.reader import Reader
from dmsp_ssm._internal.validator.validator import Validator

pytestmark = pytest.mark.unit


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


def test_exception_policy_invalid_options_type_is_api_error() -> None:
    reader = Reader()

    with pytest.raises(TypeError, match="ParseOptions"):
        reader.parse("test.dat", options=object())  # type: ignore[arg-type]


def test_exception_policy_incompatible_validator_report_is_api_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "input.dat"
    source_file.write_bytes(b"raw-stream")

    def fake_validate(self: Validator, raw_bytes: bytes) -> object:
        return {"status": "ok"}

    monkeypatch.setattr(Validator, "validate", fake_validate)
    reader = Reader()

    with pytest.raises(ValueError, match="validated_chunks"):
        reader.parse(source_file)


def test_report_policy_trailing_bytes_is_data_error_in_report_without_exception(
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
