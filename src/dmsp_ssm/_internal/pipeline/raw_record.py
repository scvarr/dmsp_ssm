"""Внутренняя модель сырой записи на границе `parser -> decoder`."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RawRecord:
    """Результат разбора одной бинарной записи до применения decode-преобразований.

    Модель используется только внутри pipeline и не входит в публичный API.
    """

    raw_bytes: bytes
    header: dict[str, int | float | str]
    blocks: dict[str, list[dict[str, int | float | str]]]
    footer: dict[str, int | float | str]
