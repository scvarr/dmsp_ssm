"""Диагностика пропущенных минут в результате обработки."""

from __future__ import annotations

import xarray as xr

from .file_parse_result import FileParseResult

MINUTES_PER_DAY = 1440


def inject_missing_minutes_summary(
    *,
    report: object,
    records: object,
    include_missing_minute_ranges: bool,
    file_results: list[FileParseResult] | None = None,
) -> None:
    """Добавить агрегированную диагностику пропущенных минут в report.summary."""

    if isinstance(report, dict):
        summary = report.get("summary")
        if not isinstance(summary, dict):
            summary = {}
            report["summary"] = summary
    elif hasattr(report, "summary"):
        summary = getattr(report, "summary")
        if not isinstance(summary, dict):
            return
    else:
        return

    file_count = summary.get("file_count")
    if not isinstance(file_count, int) or file_count < 1:
        file_count = 1

    expected_record_count = MINUTES_PER_DAY * file_count
    if hasattr(records, "sizes") and isinstance(getattr(records, "sizes"), dict):
        observed_record_count = int(getattr(records, "sizes").get("record", 0))
    elif hasattr(records, "sizes") and "record" in getattr(records, "sizes"):
        observed_record_count = int(getattr(records, "sizes")["record"])
    elif isinstance(records, list):
        observed_record_count = len(records)
    else:
        observed_record_count = 0
    missing_record_count = max(0, expected_record_count - observed_record_count)

    summary["expected_record_count"] = expected_record_count
    summary["missing_record_count"] = missing_record_count
    summary["has_missing_records"] = missing_record_count > 0

    minute_indices = _collect_present_minute_indices(records=records)
    if minute_indices:
        first_minute_index = min(minute_indices)
        last_minute_index = max(minute_indices)
        unique_minute_indices = set(minute_indices)
        unique_count = len(unique_minute_indices)
        covered_range_count = last_minute_index - first_minute_index + 1
        gap_count = max(0, covered_range_count - unique_count)

        summary["first_minute_index"] = first_minute_index
        summary["last_minute_index"] = last_minute_index
        summary["gap_count"] = gap_count

        if include_missing_minute_ranges:
            summary["missing_minute_ranges"] = build_missing_minute_ranges(
                present_minute_indices=unique_minute_indices
            )
    elif include_missing_minute_ranges:
        summary["missing_minute_ranges"] = [
            {
                "start_minute": 0,
                "end_minute": MINUTES_PER_DAY - 1,
                "count": MINUTES_PER_DAY,
            }
        ]

    if (
        include_missing_minute_ranges
        and file_results is not None
        and len(file_results) > 1
    ):
        summary["missing_minute_ranges_by_file"] = (
            build_missing_minute_ranges_by_file(file_results=file_results)
        )


def _collect_present_minute_indices(*, records: object) -> list[int]:
    """Собрать индексы присутствующих минут из результата обработки."""

    minute_indices: list[int] = []
    if isinstance(records, xr.Dataset):
        if "minute_start_sec_of_day" in records.data_vars:
            _extend_minute_indices(
                minute_indices=minute_indices,
                second_values=records["minute_start_sec_of_day"].values.tolist(),
            )
    elif isinstance(records, dict) and "minute_start_sec_of_day" in records:
        second_values = records["minute_start_sec_of_day"]
        _extend_minute_indices(
            minute_indices=minute_indices,
            second_values=_to_list(second_values),
        )
    elif isinstance(records, list):
        for record in records:
            header = getattr(record, "header", None)
            if not isinstance(header, dict):
                continue

            second_value = header.get("first_minute_first_second_time")
            if not isinstance(second_value, (int, float)):
                continue

            minute_index = int(second_value // 60)
            if 0 <= minute_index < 1440:
                minute_indices.append(minute_index)

    return minute_indices


def _extend_minute_indices(
    *,
    minute_indices: list[int],
    second_values: list[object],
) -> None:
    """Добавить валидные индексы минут из секунд от начала суток."""

    for second_value in second_values:
        if not isinstance(second_value, (int, float)):
            continue
        minute_index = int(second_value // 60)
        if 0 <= minute_index < MINUTES_PER_DAY:
            minute_indices.append(minute_index)


def _to_list(value: object) -> list[object]:
    """Преобразовать входное значение в список скаляров для анализа минут."""

    if isinstance(value, list):
        return value
    if hasattr(value, "tolist"):
        converted = value.tolist()
        if isinstance(converted, list):
            return converted
        return [converted]
    return []


def build_missing_minute_ranges(
    *,
    present_minute_indices: set[int],
) -> list[dict[str, int]]:
    """Построить компактные диапазоны отсутствующих минут в пределах суток."""

    missing_minute_indices = [
        minute
        for minute in range(MINUTES_PER_DAY)
        if minute not in present_minute_indices
    ]
    if not missing_minute_indices:
        return []

    ranges: list[dict[str, int]] = []
    range_start = missing_minute_indices[0]
    range_end = range_start

    for minute in missing_minute_indices[1:]:
        if minute == range_end + 1:
            range_end = minute
            continue

        ranges.append(
            {
                "start_minute": range_start,
                "end_minute": range_end,
                "count": range_end - range_start + 1,
            }
        )
        range_start = minute
        range_end = minute

    ranges.append(
        {
            "start_minute": range_start,
            "end_minute": range_end,
            "count": range_end - range_start + 1,
        }
    )
    return ranges


def build_missing_minute_ranges_by_file(
    *,
    file_results: list[FileParseResult],
) -> list[dict[str, object]]:
    """Построить диагностику пропущенных минут отдельно для каждого файла."""

    summaries: list[dict[str, object]] = []
    for file_result in file_results:
        minute_indices = _collect_present_minute_indices_from_raw_records(
            records=file_result.records,
        )
        unique_minute_indices = set(minute_indices)
        missing_ranges = build_missing_minute_ranges(
            present_minute_indices=unique_minute_indices,
        )
        missing_record_count = sum(
            missing_range["count"] for missing_range in missing_ranges
        )
        summary: dict[str, object] = {
            "source_file": file_result.source_file.path.name,
            "expected_record_count": MINUTES_PER_DAY,
            "observed_record_count": len(file_result.records),
            "missing_record_count": missing_record_count,
            "has_missing_records": missing_record_count > 0,
            "first_minute_index": None,
            "last_minute_index": None,
            "gap_count": 0,
            "missing_minute_ranges": missing_ranges,
        }
        if unique_minute_indices:
            first_minute_index = min(unique_minute_indices)
            last_minute_index = max(unique_minute_indices)
            summary["first_minute_index"] = first_minute_index
            summary["last_minute_index"] = last_minute_index
            summary["gap_count"] = _calculate_gap_count(
                present_minute_indices=unique_minute_indices,
                first_minute_index=first_minute_index,
                last_minute_index=last_minute_index,
            )
        summaries.append(summary)
    return summaries


def _collect_present_minute_indices_from_raw_records(
    *,
    records: object,
) -> list[int]:
    """Собрать индексы минут из raw-записей одного файла."""

    minute_indices: list[int] = []
    if not isinstance(records, list):
        return minute_indices

    for record in records:
        header = getattr(record, "header", None)
        if not isinstance(header, dict):
            continue
        millisecond_value = header.get("first_minute_first_second_time")
        if not isinstance(millisecond_value, (int, float)):
            continue
        minute_index = int(millisecond_value // 60000)
        if 0 <= minute_index < MINUTES_PER_DAY:
            minute_indices.append(minute_index)
    return minute_indices


def _calculate_gap_count(
    *,
    present_minute_indices: set[int],
    first_minute_index: int,
    last_minute_index: int,
) -> int:
    """Посчитать число пропусков внутри покрытого диапазона минут."""

    covered_range_count = last_minute_index - first_minute_index + 1
    return max(0, covered_range_count - len(present_minute_indices))
