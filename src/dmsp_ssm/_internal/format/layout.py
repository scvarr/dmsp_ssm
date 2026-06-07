from __future__ import annotations

from typing import Any


def build_field_definitions(
    format_definition: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Собрать индекс полей формата по имени."""
    field_definitions: dict[str, dict[str, Any]] = {}

    for field in format_definition.get("header", []):
        field_definitions[field["name"]] = field

    for field in format_definition.get("footer", []):
        field_definitions[field["name"]] = field

    return field_definitions
