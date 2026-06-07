"""Внутренняя модель декодированной записи DMSP SSM."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class DecodedRecord:
    """Граница данных между decoder-слоем и builder-слоем.

    Значения в модели уже приведены к декодированному представлению согласно
    правилам преобразования формата.
    """

    header: dict[str, int | float | str]
    blocks: dict[str, list[dict[str, int | float | str]]]
    footer: dict[str, int | float | str]
