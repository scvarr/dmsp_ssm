"""Низкоуровневое чтение raw-значений из бинарной записи."""

from __future__ import annotations

from typing import Any, Literal


class BinaryFieldReader:
    """Чтение целочисленных raw-полей по offset/size из описания формата."""

    def __init__(self, *, byte_order: Literal["little", "big"]) -> None:
        self.byte_order = byte_order

    def read_raw_int(
        self,
        *,
        record: bytes,
        field_definition: dict[str, Any],
    ) -> int:
        """Прочитать целочисленное raw-значение поля из бинарной записи."""
        field_type = field_definition.get("type")
        if field_type != "int":
            field_name = field_definition.get("name", "<unknown>")
            raise ValueError(
                f"Неподдерживаемый raw-тип поля '{field_type}' для поля '{field_name}'. "
                "Поддерживается только type='int'."
            )

        start = int(field_definition["offset"])
        size = int(field_definition["size"])
        end = start + size

        return int.from_bytes(
            record[start:end],
            byteorder=self.byte_order,
            signed=True,
        )
