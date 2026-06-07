"""Обработка отдельных файлов внутри сценария коллекции."""

from __future__ import annotations

from collections.abc import Callable, Iterator
import re
from typing import Any, Protocol

from .collection_error_policy import CollectionErrorPolicy
from .file_parse_result import FileParseResult
from .protocols import SupportsSourceFileRead
from ..pipeline.field_trace import FieldTrace
from ..pipeline.field_trace_extractor import extract_field_traces
from ..pipeline.raw_record import RawRecord
from ..source.data_source import SourceFile


UNKNOWN_FLIGHT_NUMBER = -1000
_SOURCE_FILE_FLIGHT_NUMBER_PATTERN = re.compile(
    r"^m(?P<flight_number>\d{2})\d{5}\.dat(?:\.gz)?$",
    re.IGNORECASE,
)


class SupportsTraceFormatDefinition(Protocol):
    """Минимальный контракт описания формата для извлечения `FieldTrace`."""

    def as_dict(self) -> dict[str, Any]: ...


def parse_source_file(
    *,
    data_source: SupportsSourceFileRead,
    source_file: SourceFile,
    validate_raw_bytes: Callable[[bytes], object],
    parse_record: Callable[[bytes], object],
    extract_validated_chunks: Callable[..., list[bytes]],
    format_definition: SupportsTraceFormatDefinition,
) -> FileParseResult:
    """Прочитать, провалидировать и разобрать один файл источника."""

    raw_bytes = data_source.read_source_file(source_file)
    validation_report = validate_raw_bytes(raw_bytes)
    validated_chunks = extract_validated_chunks(validation_report=validation_report)
    records = [
        _normalize_record_flight_number(
            record=parse_record(chunk),  # type: ignore[arg-type]
            source_file=source_file,
        )
        for chunk in validated_chunks
    ]
    definition = format_definition.as_dict()
    record_size = int(definition["record_size"])
    field_traces: list[FieldTrace] = []
    for record_index, chunk in enumerate(validated_chunks):
        if len(chunk) < record_size:
            continue
        field_traces.extend(
            extract_field_traces(
                chunk=chunk,
                record_index=record_index,
                format_definition=format_definition,
            )
        )
    return FileParseResult(
        source_file=source_file,
        records=records,
        field_traces=field_traces,
        report=validation_report,
    )


def _normalize_record_flight_number(
    *,
    record: object,
    source_file: SourceFile,
) -> RawRecord:
    """Нормализовать номер аппарата в записи по footer или имени файла."""

    if not isinstance(record, RawRecord):
        return record  # type: ignore[return-value]
    if "flight_number" not in record.footer:
        return record

    raw_flight_number = _as_int_or_none(record.footer["flight_number"])
    if raw_flight_number is not None and 0 <= raw_flight_number <= 20:
        record.footer["flight_number"] = raw_flight_number
        return record

    record.footer["flight_number"] = _extract_flight_number_from_source_file(
        source_file=source_file,
    )
    return record


def _as_int_or_none(value: object) -> int | None:
    """Вернуть целое значение или None, если преобразование невозможно."""

    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _extract_flight_number_from_source_file(*, source_file: SourceFile) -> int:
    """Извлечь номер аппарата из имени файла или вернуть sentinel."""

    match = _SOURCE_FILE_FLIGHT_NUMBER_PATTERN.match(source_file.path.name)
    if match is None:
        return UNKNOWN_FLIGHT_NUMBER
    return int(match.group("flight_number"))


def process_source_file_with_policy(
    *,
    data_source: SupportsSourceFileRead,
    source_file: SourceFile,
    validate_raw_bytes: Callable[[bytes], object],
    parse_record: Callable[[bytes], object],
    extract_validated_chunks: Callable[..., list[bytes]],
    format_definition: SupportsTraceFormatDefinition,
    policy: str,
) -> FileParseResult | None:
    """Обработать один файл с учетом политики ошибок коллекции."""

    if policy not in CollectionErrorPolicy.ALL:
        raise ValueError(
            f"Недопустимая политика обработки коллекции файлов: {policy}"
        )

    try:
        return parse_source_file(
            data_source=data_source,
            source_file=source_file,
            validate_raw_bytes=validate_raw_bytes,
            parse_record=parse_record,
            extract_validated_chunks=extract_validated_chunks,
            format_definition=format_definition,
        )
    except Exception:
        if policy == CollectionErrorPolicy.SKIP_FAILED_FILE:
            return None
        raise


def iter_file_parse_results(
    *,
    data_source: SupportsSourceFileRead,
    source_files: list[SourceFile],
    validate_raw_bytes: Callable[[bytes], object],
    parse_record: Callable[[bytes], object],
    extract_validated_chunks: Callable[..., list[bytes]],
    format_definition: SupportsTraceFormatDefinition,
    policy: str,
) -> Iterator[FileParseResult]:
    """Итерировать file-level результаты в исходном порядке файлов."""

    for source_file in source_files:
        file_result = process_source_file_with_policy(
            data_source=data_source,
            source_file=source_file,
            validate_raw_bytes=validate_raw_bytes,
            parse_record=parse_record,
            extract_validated_chunks=extract_validated_chunks,
            format_definition=format_definition,
            policy=policy,
        )
        if file_result is not None:
            yield file_result


def map_source_files_to_results(
    *,
    data_source: SupportsSourceFileRead,
    source_files: list[SourceFile],
    validate_raw_bytes: Callable[[bytes], object],
    parse_record: Callable[[bytes], object],
    extract_validated_chunks: Callable[..., list[bytes]],
    format_definition: SupportsTraceFormatDefinition,
    policy: str,
) -> list[FileParseResult]:
    """Преобразовать файлы источника в file-level результаты в исходном порядке."""
    return list(
        iter_file_parse_results(
            data_source=data_source,
            source_files=source_files,
            validate_raw_bytes=validate_raw_bytes,
            parse_record=parse_record,
            extract_validated_chunks=extract_validated_chunks,
            format_definition=format_definition,
            policy=policy,
        )
    )


def parse_source_files_collection(
    *,
    data_source: SupportsSourceFileRead,
    source_files: list[SourceFile],
    validate_raw_bytes: Callable[[bytes], object],
    parse_record: Callable[[bytes], object],
    extract_validated_chunks: Callable[..., list[bytes]],
    format_definition: SupportsTraceFormatDefinition,
    policy: str,
) -> list[FileParseResult]:
    """Обработать коллекцию файлов и вернуть file-level результаты."""

    return map_source_files_to_results(
        data_source=data_source,
        source_files=source_files,
        validate_raw_bytes=validate_raw_bytes,
        parse_record=parse_record,
        extract_validated_chunks=extract_validated_chunks,
        format_definition=format_definition,
        policy=policy,
    )
