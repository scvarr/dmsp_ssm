"""Обработка отдельных файлов внутри сценария коллекции."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any, Protocol

from .collection_error_policy import CollectionErrorPolicy
from .file_parse_result import FileParseResult
from .protocols import SupportsSourceFileRead
from ..pipeline.field_trace import FieldTrace
from ..pipeline.field_trace_extractor import extract_field_traces
from ..source.data_source import SourceFile


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
    records = [parse_record(chunk) for chunk in validated_chunks]
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
        records=records,  # type: ignore[arg-type]
        field_traces=field_traces,
        report=validation_report,
    )


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
