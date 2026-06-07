"""Валидация внутреннего описания бинарного формата DMSP SSM."""

from __future__ import annotations

from typing import Any

from .layout import build_field_definitions


class FormatDefinitionValidator:
    """Проверка обязательных секций и полей описания формата."""

    REQUIRED_KEYS = ("record_size", "byte_order", "validation_fields")

    def validate(self, format_definition: dict[str, Any]) -> None:
        """Проверить обязательные ключи и поля, используемые validator-слоем."""
        for key in self.REQUIRED_KEYS:
            if key not in format_definition:
                raise ValueError(
                    f"В описании формата SSM отсутствует обязательный ключ: {key}"
                )

        field_definitions = build_field_definitions(format_definition)
        for field_name in format_definition["validation_fields"]:
            if field_name not in field_definitions:
                raise ValueError(
                    "Поле, указанное в validation_fields, не найдено "
                    f"в layout описания формата SSM: {field_name}"
                )
