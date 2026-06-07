"""Разбор валидированной бинарной записи в `RawRecord`."""

from __future__ import annotations

from typing import Any

from ..format.definition_validator import FormatDefinitionValidator
from ..format.raw_field_reader import BinaryFieldReader
from .raw_record import RawRecord


class RecordParser:
    """Разборщик одной валидированной минутной записи DMSP SSM."""

    def __init__(
        self,
        *,
        format_definition: dict[str, Any],
        field_reader: BinaryFieldReader | None = None,
    ) -> None:
        FormatDefinitionValidator().validate(format_definition)

        self.record_size = int(format_definition["record_size"])
        byte_order = format_definition["byte_order"]

        if byte_order not in {"little", "big"}:
            raise ValueError(f"Неподдерживаемый byte_order: {byte_order}")
        self.byte_order = byte_order
        self.header_field_definitions = list(format_definition.get("header", []))
        self.footer_field_definitions = list(format_definition.get("footer", []))
        self.block_definitions = list(format_definition.get("blocks", []))
        self._field_reader = field_reader or BinaryFieldReader(
            byte_order=self.byte_order
        )

    def parse_record(self, record: bytes) -> RawRecord:
        """Разобрать одну бинарную запись в `RawRecord`."""

        if len(record) != self.record_size:
            raise ValueError(
                f"Размер записи не совпадает с format_definition.record_size: "
                f"{len(record)} != {self.record_size}"
            )

        header = self._read_layout_fields(
            record=record,
            field_definitions=self.header_field_definitions,
        )
        blocks = self._read_blocks(record=record)
        footer = self._read_layout_fields(
            record=record,
            field_definitions=self.footer_field_definitions,
        )

        return RawRecord(
            raw_bytes=record,
            header=header,
            blocks=blocks,
            footer=footer,
        )

    def _read_layout_fields(
        self,
        *,
        record: bytes,
        field_definitions: list[dict[str, Any]],
        base_offset: int = 0,
    ) -> dict[str, int | float | str]:
        values: dict[str, int | float | str] = {}
        for field_definition in field_definitions:
            absolute_field_definition = dict(field_definition)
            absolute_field_definition["offset"] = (
                base_offset + int(field_definition["offset"])
            )
            values[field_definition["name"]] = self._field_reader.read_raw_int(
                record=record,
                field_definition=absolute_field_definition,
            )
        return values

    def _read_blocks(
        self,
        *,
        record: bytes,
    ) -> dict[str, list[dict[str, int | float | str]]]:
        blocks: dict[str, list[dict[str, int | float | str]]] = {}

        for block_definition in self.block_definitions:
            block_name = block_definition["name"]
            repeat = int(block_definition["repeat"])
            stride = int(block_definition["stride"])
            start_offset = int(block_definition["start_offset"])
            field_definitions = list(block_definition.get("fields", []))

            repeats: list[dict[str, int | float | str]] = []
            for index in range(repeat):
                base_offset = start_offset + (index * stride)
                repeats.append(
                    self._read_layout_fields(
                        record=record,
                        field_definitions=field_definitions,
                        base_offset=base_offset,
                    )
                )

            blocks[block_name] = repeats

        return blocks
