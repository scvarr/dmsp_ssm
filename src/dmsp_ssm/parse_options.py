"""Публичные параметры вызова `Reader.parse`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass(slots=True)
class ParseOptions:
    """Настройки чтения, валидации и выбора выходного профиля.

    `output_profile` определяет форму данных в `ParseResult.records`.
    Публично поддерживаются профили `xarray`, `numpy` и `table`.
    """

    PUBLIC_OUTPUT_PROFILES: ClassVar[frozenset[str]] = frozenset(
        {"xarray", "numpy", "table"}
    )

    recursive: bool = True
    error_policy: str | None = None
    include_missing_minute_ranges: bool = False
    output_profile: str = "xarray"

    def __post_init__(self) -> None:
        if self.output_profile not in self.PUBLIC_OUTPUT_PROFILES:
            raise ValueError(
                "Параметр output_profile должен быть одним из: xarray, numpy, table."
            )
