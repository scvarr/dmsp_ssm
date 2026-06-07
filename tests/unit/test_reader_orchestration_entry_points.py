import inspect

import pytest

import dmsp_ssm.reader as reader_module
from dmsp_ssm.parse_options import ParseOptions
from dmsp_ssm.parse_result import ParseResult
from dmsp_ssm.reader import Reader
from dmsp_ssm._internal.validator.contracts import ValidationResult

pytestmark = pytest.mark.unit


def test_reader_imports_compact_orchestration_entry_points_instead_of_submodules() -> None:
    source_code = inspect.getsource(reader_module)

    assert "dmsp_ssm._internal.orchestration.raw_collection_assembly" not in source_code
    assert "dmsp_ssm._internal.orchestration.report_aggregation" not in source_code
    assert "dmsp_ssm._internal.orchestration.collection_error_policy" not in source_code


def test_reader_parse_delegates_to_internal_use_case_with_normalized_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_run_reader_parse_use_case(**kwargs: object) -> ParseResult:
        captured.update(kwargs)
        return ParseResult(
            records="sentinel",
            report=ValidationResult(status="ok"),
        )

    monkeypatch.setattr(
        reader_module,
        "run_reader_parse_use_case",
        fake_run_reader_parse_use_case,
    )

    reader = Reader(pre_parse_size_warning_threshold_bytes=123)
    result = reader.parse(
        "input",
        options=ParseOptions(
            recursive=False,
            error_policy="strict",
            output_profile="xarray",
        ),
        recursive=True,
        include_missing_minute_ranges=True,
    )

    assert result.records == "sentinel"
    assert captured["path"] == "input"
    assert captured["default_error_policy"] == reader._default_error_policy
    assert captured["runtime"] is reader._runtime
    assert captured["output_profile"] == "xarray"
    assert captured["pre_parse_size_warning_threshold_bytes"] == 123
    assert captured["options"] == ParseOptions(
        recursive=True,
        error_policy="strict",
        include_missing_minute_ranges=True,
        output_profile="xarray",
    )
