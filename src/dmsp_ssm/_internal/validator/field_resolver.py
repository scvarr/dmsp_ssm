"""Разрешение полей формата, используемых при валидации."""

from __future__ import annotations

from typing import Any

from ..format.layout import build_field_definitions


class ValidationFieldResolver:
    """Разрешение описаний полей, участвующих в валидации."""

    def __init__(self, *, format_definition: dict[str, Any]) -> None:
        self._format_definition = format_definition
        self.field_definitions = build_field_definitions(format_definition)

    def resolve(self) -> dict[str, dict[str, Any]]:
        """Вернуть описания полей, перечисленных в `validation_fields`."""
        validation_fields = list(self._format_definition["validation_fields"])
        return {
            field_name: self.field_definitions[field_name]
            for field_name in validation_fields
        }
