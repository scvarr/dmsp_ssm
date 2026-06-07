import pytest

from dmsp_ssm.parse_result import ParseResult
from dmsp_ssm._internal.validator.contracts import ValidationResult

pytestmark = pytest.mark.unit


def test_ssm_parse_result_contains_records_and_report() -> None:
    records = {"record_count": 1}
    report = ValidationResult(status="ok", validated_chunks=[b"\x00"])

    result = ParseResult(records=records, report=report)

    assert result.records == records
    assert result.report is report
    assert result.metadata is None
    assert result.extensions is None


def test_ssm_parse_result_requires_records_field() -> None:
    report = ValidationResult(status="ok", validated_chunks=[])

    with pytest.raises(TypeError):
        ParseResult(report=report)  # type: ignore[call-arg]


def test_ssm_parse_result_requires_report_field() -> None:
    records = {"record_count": 0}

    with pytest.raises(TypeError):
        ParseResult(records=records)  # type: ignore[call-arg]


def test_ssm_parse_result_supports_metadata_and_extensions_without_breaking_core() -> None:
    records = {"record_count": 7}
    report = ValidationResult(status="ok", validated_chunks=[b"\x01"])
    metadata = {"source_count": 1}
    extensions = {"future_flag": True}

    result = ParseResult(
        records=records,
        report=report,
        metadata=metadata,
        extensions=extensions,
    )

    assert result.records == records
    assert result.report is report
    assert result.metadata == metadata
    assert result.extensions == extensions


def test_ssm_parse_result_does_not_expose_alternative_data_fields() -> None:
    records = {"record_count": 3}
    report = ValidationResult(status="ok", validated_chunks=[])
    result = ParseResult(records=records, report=report)

    assert not hasattr(result, "artifact")
    assert not hasattr(result, "decoded")


def test_ssm_parse_result_equality_compares_all_public_fields() -> None:
    report = ValidationResult(status="ok", validated_chunks=[b"\x01"])
    left = ParseResult(
        records={"rows": [1]},
        report=report,
        metadata={"source": "unit"},
        extensions={"flag": True},
    )
    right = ParseResult(
        records={"rows": [1]},
        report=ValidationResult(status="ok", validated_chunks=[b"\x01"]),
        metadata={"source": "unit"},
        extensions={"flag": True},
    )

    assert left == right

    changed = ParseResult(
        records={"rows": [2]},
        report=ValidationResult(status="ok", validated_chunks=[b"\x01"]),
        metadata={"source": "unit"},
        extensions={"flag": True},
    )
    assert left != changed


def test_ssm_parse_result_equality_with_non_parse_result_returns_false() -> None:
    result = ParseResult(
        records={"rows": [1]},
        report=ValidationResult(status="ok", validated_chunks=[]),
    )

    assert (result == object()) is False
