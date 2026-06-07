"""Контракты результата валидации бинарного потока."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, TypedDict


class ValidationRecordContext(TypedDict):
    """Контекст соседней валидной записи для диагностики инцидентов."""

    offset: int
    validation_fields: dict[str, int]


@dataclass(slots=True)
class ValidationResult:
    """Результат валидации бинарного потока.

    `validated_chunks` используется только как внутренняя передача данных к этапу
    разбора записей. Перед возвратом фасадного `ParseResult` сырые chunks удаляются
    из диагностического отчета.

    `summary` хранит агрегированную диагностику, включая сведения о неполноте
    набора записей и пропущенных минутах.
    """

    status: str
    outcome: Literal["fatal", "nonfatal"] = "nonfatal"
    validated_chunks: list[bytes] = field(default_factory=list, repr=False)
    incidents: list[Any] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ValidationIncident:
    """Инцидент, найденный при валидации потока."""

    kind: str

    start_offset: int
    end_offset: int

    message: str

    previous_context: ValidationRecordContext | None = None
    next_context: ValidationRecordContext | None = None
    estimated_missing_records: int | None = None
