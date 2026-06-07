"""Граница декодирования `RawRecord` в `DecodedRecord`."""
from __future__ import annotations

from typing import Any

from ..pipeline.raw_record import RawRecord
from ..pipeline.decoded_record import DecodedRecord
from .transform import apply_transform


class Decoder:
    """Преобразование сырой записи в декодированную запись.

    На вход принимается `RawRecord`, на выходе формируется `DecodedRecord`.
    Структура секций `header`, `blocks` и `footer` сохраняется.

    Ошибки доступа к полям и применения transform-выражений поднимаются как
    исключения. Диагностический отчет на этом слое не формируется.
    """

    def __init__(self, format_definition: dict[str, Any]) -> None:
        self._format_definition = format_definition
        self._header_field_definitions = list(format_definition.get("header", []))
        self._block_definitions = list(format_definition.get("blocks", []))
        self._footer_field_definitions = list(format_definition.get("footer", []))

    def decode(self, record: RawRecord) -> DecodedRecord:
        """Декодировать один `RawRecord` без изменения структуры секций."""

        decoded_header: dict[str, int | float | str] = {}
        for field_definition in self._header_field_definitions:
            field_name = field_definition["name"]
            raw_value = record.header[field_name]
            decoded_header[field_name] = apply_transform(
                raw_value=raw_value,
                field_definition=field_definition,
            )

        decoded_blocks: dict[str, list[dict[str, int | float | str]]] = {}
        for block_definition in self._block_definitions:
            block_name = block_definition["name"]
            repeat = int(block_definition["repeat"])
            field_definitions = list(block_definition.get("fields", []))
            raw_repeats = record.blocks[block_name]

            decoded_repeats: list[dict[str, int | float | str]] = []
            for index in range(repeat):
                raw_repeat = raw_repeats[index]
                decoded_repeat: dict[str, int | float | str] = {}
                for field_definition in field_definitions:
                    field_name = field_definition["name"]
                    raw_value = raw_repeat[field_name]
                    decoded_repeat[field_name] = apply_transform(
                        raw_value=raw_value,
                        field_definition=field_definition,
                    )
                decoded_repeats.append(decoded_repeat)

            decoded_blocks[block_name] = decoded_repeats

        decoded_footer: dict[str, int | float | str] = {}
        for field_definition in self._footer_field_definitions:
            field_name = field_definition["name"]
            raw_value = record.footer[field_name]
            decoded_footer[field_name] = apply_transform(
                raw_value=raw_value,
                field_definition=field_definition,
            )

        return DecodedRecord(
            header=decoded_header,
            blocks=decoded_blocks,
            footer=decoded_footer,
        )
