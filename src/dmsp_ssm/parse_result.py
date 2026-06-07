"""Публичная модель результата обработки файлов DMSP SSM."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from ._internal.validator.contracts import ValidationResult

# Тип records зависит от выбранного output_profile и не привязан к internal-моделям.
FacadeRecords: TypeAlias = object


@dataclass(slots=True)
class ParseResult:
    """Результат выполнения `Reader.parse`.

    Поле `records` содержит основной результат обработки. Его тип зависит от
    выбранного `output_profile`: `xarray`, `numpy` или `table`.

    Поле `report` содержит диагностический отчет. Поля `metadata` и
    `extensions` предназначены для служебных сведений и прикладных расширений,
    не изменяющих основной канал данных.
    """

    records: FacadeRecords
    report: ValidationResult
    metadata: dict[str, object] | None = None
    extensions: dict[str, object] | None = None

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ParseResult):
            return (
                self.records == other.records
                and self.report == other.report
                and self.metadata == other.metadata
                and self.extensions == other.extensions
            )
        return False
