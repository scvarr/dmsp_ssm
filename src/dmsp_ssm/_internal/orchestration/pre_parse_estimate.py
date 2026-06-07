"""Оценка входного объема до обработки коллекции."""

from __future__ import annotations

from ..source.data_source import SourceFile


def estimate_pre_parse_input(
    *,
    source_files: list[SourceFile],
    record_size: int,
    threshold_bytes: int,
) -> dict[str, object]:
    """Вернуть эвристическую оценку входного объема до обработки."""

    total_input_bytes = 0
    for source_file in source_files:
        try:
            total_input_bytes += source_file.path.stat().st_size
        except OSError:
            # Оценка не должна блокировать основной процесс обработки.
            continue

    estimated_record_count = total_input_bytes // record_size if record_size > 0 else 0
    warning = total_input_bytes > threshold_bytes

    return {
        "total_input_bytes": total_input_bytes,
        "estimated_record_count": estimated_record_count,
        "threshold_bytes": threshold_bytes,
        "warning": warning,
    }


def inject_pre_parse_estimate_into_report(
    *,
    report: object,
    estimate: dict[str, object],
) -> None:
    """Добавить диагностику входного объема в report.summary, если включено предупреждение."""

    if not bool(estimate.get("warning", False)):
        return

    diagnostic = {
        "kind": "pre_parse_input_size_warning",
        "total_input_bytes": estimate["total_input_bytes"],
        "estimated_record_count": estimate["estimated_record_count"],
        "threshold_bytes": estimate["threshold_bytes"],
        "message": (
            "Оценка входного объема превышает порог предупреждения; итоговый "
            "результат в памяти может быть большим."
        ),
    }

    if isinstance(report, dict):
        summary = report.get("summary")
        if not isinstance(summary, dict):
            summary = {}
            report["summary"] = summary
        summary["pre_parse_input_estimate"] = diagnostic
        return

    if hasattr(report, "summary"):
        summary = getattr(report, "summary")
        if isinstance(summary, dict):
            summary["pre_parse_input_estimate"] = diagnostic
