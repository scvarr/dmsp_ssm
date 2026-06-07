"""Внутренняя модель трассировки сырого поля записи."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class FieldTrace:
    """Описание одного поля записи для table trace-представления.

    Модель хранит расположение поля, его роль, сырое значение и сведения,
    необходимые для сопоставления raw, decoded и normalized значений.
    """

    record_index: int
    second_index: int | None
    section: str
    field_name: str
    field_role: str
    byte_offset: int | None
    byte_length: int | None
    raw_hex: str | None
    raw_int: int | None
    unit: str | None
    transform: str | None
