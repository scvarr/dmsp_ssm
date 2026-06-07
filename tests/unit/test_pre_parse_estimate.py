from __future__ import annotations

from pathlib import Path

import pytest

from dmsp_ssm._internal.orchestration.pre_parse_estimate import (
    estimate_pre_parse_input,
    inject_pre_parse_estimate_into_report,
)
from dmsp_ssm._internal.source import SourceFile

pytestmark = pytest.mark.unit


def test_estimate_pre_parse_input_sums_sizes_and_sets_warning() -> None:
    first = SourceFile(path=Path(__file__), kind="dat")
    second = SourceFile(path=Path(__file__), kind="dat")

    estimate = estimate_pre_parse_input(
        source_files=[first, second],
        record_size=10,
        threshold_bytes=1,
    )

    assert estimate["total_input_bytes"] > 0
    assert estimate["estimated_record_count"] == estimate["total_input_bytes"] // 10
    assert estimate["threshold_bytes"] == 1
    assert estimate["warning"] is True


def test_estimate_pre_parse_input_skips_files_with_stat_errors() -> None:
    missing = SourceFile(path=Path("definitely_missing_file.dat"), kind="dat")

    estimate = estimate_pre_parse_input(
        source_files=[missing],
        record_size=4,
        threshold_bytes=1,
    )

    assert estimate["total_input_bytes"] == 0
    assert estimate["estimated_record_count"] == 0
    assert estimate["warning"] is False


def test_estimate_pre_parse_input_returns_zero_records_for_non_positive_record_size() -> None:
    source = SourceFile(path=Path(__file__), kind="dat")

    estimate = estimate_pre_parse_input(
        source_files=[source],
        record_size=0,
        threshold_bytes=10**12,
    )

    assert estimate["total_input_bytes"] > 0
    assert estimate["estimated_record_count"] == 0
    assert estimate["warning"] is False


def test_inject_pre_parse_estimate_into_report_does_nothing_without_warning() -> None:
    report = {"summary": {"existing": 1}}
    estimate = {
        "total_input_bytes": 100,
        "estimated_record_count": 10,
        "threshold_bytes": 200,
        "warning": False,
    }

    inject_pre_parse_estimate_into_report(report=report, estimate=estimate)

    assert report == {"summary": {"existing": 1}}


def test_inject_pre_parse_estimate_into_report_creates_summary_for_dict_report() -> None:
    report: dict[str, object] = {"summary": "bad-summary-type"}
    estimate = {
        "total_input_bytes": 500,
        "estimated_record_count": 50,
        "threshold_bytes": 100,
        "warning": True,
    }

    inject_pre_parse_estimate_into_report(report=report, estimate=estimate)

    summary = report["summary"]
    assert isinstance(summary, dict)
    diagnostic = summary["pre_parse_input_estimate"]
    assert diagnostic["kind"] == "pre_parse_input_size_warning"
    assert diagnostic["total_input_bytes"] == 500
    assert diagnostic["estimated_record_count"] == 50
    assert diagnostic["threshold_bytes"] == 100
    assert "превышает порог предупреждения" in diagnostic["message"]


def test_inject_pre_parse_estimate_into_report_writes_into_object_summary_dict() -> None:
    class Report:
        def __init__(self) -> None:
            self.summary = {"existing": "ok"}

    report = Report()
    estimate = {
        "total_input_bytes": 1000,
        "estimated_record_count": 100,
        "threshold_bytes": 10,
        "warning": True,
    }

    inject_pre_parse_estimate_into_report(report=report, estimate=estimate)

    assert report.summary["existing"] == "ok"
    assert report.summary["pre_parse_input_estimate"]["total_input_bytes"] == 1000

