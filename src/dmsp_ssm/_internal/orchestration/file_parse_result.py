"""Внутренний контракт результата обработки одного файла."""

from __future__ import annotations

from dataclasses import dataclass

from ..source.data_source import SourceFile
from ..pipeline.field_trace import FieldTrace
from ..pipeline.raw_record import RawRecord


@dataclass(slots=True)
class FileParseResult:
    """Результат file-level обработки до collection-level агрегации.

    `records` и `field_traces` используют file-local индексацию записей.
    Переход к global `record_index` выполняется при сборке `RawCollectionResult`.
    """

    source_file: SourceFile
    records: list[RawRecord]
    field_traces: list[FieldTrace]
    report: object
