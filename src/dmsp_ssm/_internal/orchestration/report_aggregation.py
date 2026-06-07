"""Агрегация отчетов валидации для коллекции файлов."""

from __future__ import annotations

from typing import Any

from .file_parse_result import FileParseResult
from ..validator.contracts import ValidationResult


def aggregate_file_reports(file_results: list[FileParseResult]) -> ValidationResult:
    """Агрегировать отчеты валидации отдельных файлов в единый отчет."""

    all_incidents: list[Any] = []
    all_validated_chunks: list[bytes] = []
    candidate_record_total = 0
    file_error_count = 0
    has_fatal = False
    has_error = False

    for file_result in file_results:
        report = file_result.report
        status = _read_report_field(report, "status", "ok")
        outcome = _read_report_field(report, "outcome", "nonfatal")
        incidents = _read_report_field(report, "incidents", [])
        validated_chunks = _read_report_field(report, "validated_chunks", [])
        summary = _read_report_field(report, "summary", {})

        if status == "error":
            has_error = True
            file_error_count += 1
        if outcome == "fatal":
            has_fatal = True

        if isinstance(incidents, list):
            all_incidents.extend(incidents)
        if isinstance(validated_chunks, list):
            all_validated_chunks.extend(
                chunk for chunk in validated_chunks if isinstance(chunk, bytes)
            )
        if isinstance(summary, dict):
            candidate_value = summary.get("candidate_record_count", 0)
            if isinstance(candidate_value, int):
                candidate_record_total += candidate_value

    return ValidationResult(
        status="error" if has_error else "ok",
        outcome="fatal" if has_fatal else "nonfatal",
        validated_chunks=all_validated_chunks,
        incidents=all_incidents,
        summary={
            "file_count": len(file_results),
            "file_error_count": file_error_count,
            "candidate_record_count": candidate_record_total,
            "validated_record_count": len(all_validated_chunks),
        },
    )


def _read_report_field(report: object, field: str, default: Any) -> Any:
    if isinstance(report, dict):
        return report.get(field, default)
    if hasattr(report, field):
        return getattr(report, field)
    return default
