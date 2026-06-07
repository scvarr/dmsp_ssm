"""Извлечение `FieldTrace` из одного валидированного chunk записи."""

from __future__ import annotations

from typing import Any

from ..format.definition import FormatDefinition
from ..format.raw_trace_reader import (
    read_raw_hex,
    read_raw_int,
)
from .field_trace import FieldTrace


def extract_record_field_traces(
    *,
    chunk: bytes,
    record_index: int,
    format_definition: FormatDefinition,
) -> list[FieldTrace]:
    """Построить trace для record-level полей (`header`/`footer`) одного chunk."""

    definition = format_definition.as_dict()
    byte_order = str(definition["byte_order"])

    traces: list[FieldTrace] = []
    traces.extend(_build_header_traces(
        chunk=chunk,
        record_index=record_index,
        definition=definition,
        byte_order=byte_order,
    ))
    traces.extend(_build_footer_traces(
        chunk=chunk,
        record_index=record_index,
        definition=definition,
        byte_order=byte_order,
    ))
    return traces


def extract_field_traces(
    *,
    chunk: bytes,
    record_index: int,
    format_definition: FormatDefinition,
) -> list[FieldTrace]:
    """Построить общий trace одного chunk в порядке `header -> second_data -> footer`."""

    definition = format_definition.as_dict()
    byte_order = str(definition["byte_order"])

    traces: list[FieldTrace] = []
    traces.extend(_build_header_traces(
        chunk=chunk,
        record_index=record_index,
        definition=definition,
        byte_order=byte_order,
    ))
    traces.extend(_build_second_traces(
        chunk=chunk,
        record_index=record_index,
        definition=definition,
        byte_order=byte_order,
    ))
    traces.extend(_build_footer_traces(
        chunk=chunk,
        record_index=record_index,
        definition=definition,
        byte_order=byte_order,
    ))
    return traces


def extract_second_field_traces(
    *,
    chunk: bytes,
    record_index: int,
    format_definition: FormatDefinition,
) -> list[FieldTrace]:
    """Построить trace для second-level полей (`second_data`) одного chunk."""

    definition = format_definition.as_dict()
    byte_order = str(definition["byte_order"])
    return _build_second_traces(
        chunk=chunk,
        record_index=record_index,
        definition=definition,
        byte_order=byte_order,
    )


def _build_second_traces(
    *,
    chunk: bytes,
    record_index: int,
    definition: dict[str, Any],
    byte_order: str,
) -> list[FieldTrace]:
    """Построить trace-записи для полей секции `second_data`."""

    block_definition = _find_second_data_block(definition)
    if block_definition is None:
        return []

    repeat = int(block_definition["repeat"])
    stride = int(block_definition["stride"])
    start_offset = int(block_definition["start_offset"])
    field_definitions = list(block_definition.get("fields", []))

    traces: list[FieldTrace] = []
    for second_index in range(repeat):
        base_offset = start_offset + (second_index * stride)
        for field_definition in field_definitions:
            local_offset = int(field_definition["offset"])
            byte_offset = base_offset + local_offset
            byte_length = int(field_definition["size"])
            traces.append(
                FieldTrace(
                    record_index=record_index,
                    second_index=second_index,
                    section="second_data",
                    field_name=str(field_definition["name"]),
                    field_role="second",
                    byte_offset=byte_offset,
                    byte_length=byte_length,
                    raw_hex=read_raw_hex(
                        chunk=chunk,
                        byte_offset=byte_offset,
                        byte_length=byte_length,
                    ),
                    raw_int=read_raw_int(
                        chunk=chunk,
                        byte_offset=byte_offset,
                        byte_length=byte_length,
                        byte_order=byte_order,
                    ),
                    unit=_as_optional_string(field_definition.get("unit")),
                    transform=_as_optional_string(field_definition.get("transform")),
                )
            )
    return traces


def _build_header_traces(
    *,
    chunk: bytes,
    record_index: int,
    definition: dict[str, Any],
    byte_order: str,
) -> list[FieldTrace]:
    """Построить record-level trace для `header`."""

    return _build_section_traces(
        chunk=chunk,
        record_index=record_index,
        section_name="header",
        field_definitions=list(definition.get("header", [])),
        byte_order=byte_order,
    )


def _build_footer_traces(
    *,
    chunk: bytes,
    record_index: int,
    definition: dict[str, Any],
    byte_order: str,
) -> list[FieldTrace]:
    """Построить record-level trace для `footer`."""

    return _build_section_traces(
        chunk=chunk,
        record_index=record_index,
        section_name="footer",
        field_definitions=list(definition.get("footer", [])),
        byte_order=byte_order,
    )


def _build_section_traces(
    *,
    chunk: bytes,
    record_index: int,
    section_name: str,
    field_definitions: list[dict[str, Any]],
    byte_order: str,
) -> list[FieldTrace]:
    """Построить trace-записи для полей одной record-level секции."""

    traces: list[FieldTrace] = []
    for field_definition in field_definitions:
        byte_offset = int(field_definition["offset"])
        byte_length = int(field_definition["size"])
        traces.append(
            FieldTrace(
                record_index=record_index,
                second_index=None,
                section=section_name,
                field_name=str(field_definition["name"]),
                field_role="record",
                byte_offset=byte_offset,
                byte_length=byte_length,
                raw_hex=read_raw_hex(
                    chunk=chunk,
                    byte_offset=byte_offset,
                    byte_length=byte_length,
                ),
                raw_int=read_raw_int(
                    chunk=chunk,
                    byte_offset=byte_offset,
                    byte_length=byte_length,
                    byte_order=byte_order,
                ),
                unit=_as_optional_string(field_definition.get("unit")),
                transform=_as_optional_string(field_definition.get("transform")),
            )
        )
    return traces


def _find_second_data_block(definition: dict[str, Any]) -> dict[str, Any] | None:
    """Найти block definition для second-level секции `second_data`."""

    for block_definition in definition.get("blocks", []):
        if str(block_definition.get("name")) == "second_data":
            return block_definition
    return None


def _as_optional_string(value: object) -> str | None:
    """Привести metadata-поле к строке или `None`."""

    if value is None:
        return None
    return str(value)
