"""Контракт collection-level результата до стадии декодирования."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .file_parse_result import FileParseResult
from .report_aggregation import aggregate_file_reports
from ..pipeline.field_trace import FieldTrace
from ..pipeline.raw_record import RawRecord


@dataclass(slots=True)
class RawCollectionResult:
    """Агрегированный результат коллекции перед декодированием и сборкой артефакта.

    `records` содержит сырые записи в детерминированном порядке обработки файлов.
    `field_traces` используют global `record_index`, согласованный с порядком
    `records`.
    """

    records: list[RawRecord]
    field_traces: list[FieldTrace]
    report: object


def assemble_raw_collection_result(
    file_results: list[FileParseResult],
) -> RawCollectionResult:
    """Собрать collection-level результат из file-level результатов."""

    records: list[RawRecord] = []
    field_traces: list[FieldTrace] = []
    global_record_index = 0
    for file_result in file_results:
        records.extend(file_result.records)
        field_traces.extend(
            _renumber_file_traces_to_global(
                traces=file_result.field_traces,
                global_start_index=global_record_index,
            )
        )
        global_record_index += len(file_result.records)

    report = aggregate_file_reports(file_results)
    return RawCollectionResult(
        records=records,
        field_traces=field_traces,
        report=report,
    )


def _renumber_file_traces_to_global(
    *,
    traces: list[FieldTrace],
    global_start_index: int,
) -> list[FieldTrace]:
    """Перенумеровать file-local `record_index` в global collection index."""

    return [
        replace(
            trace,
            record_index=global_start_index + trace.record_index,
        )
        for trace in traces
    ]
