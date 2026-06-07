"""Сценарий обработки коллекции файлов источника."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from .collection_result_builder import build_raw_collection_result
from .file_parse_result import FileParseResult
from .file_pipeline import parse_source_files_collection
from .pre_parse_estimate import (
    estimate_pre_parse_input,
    inject_pre_parse_estimate_into_report,
)
from .raw_collection_result import RawCollectionResult
from .protocols import SupportsSourceFileRead
from ..source.data_source import SourceFile


class SupportsTraceFormatDefinition(Protocol):
    """Минимальный контракт описания формата для извлечения `FieldTrace`."""

    def as_dict(self) -> dict[str, Any]: ...


@dataclass(slots=True)
class CollectionPipelineOutput:
    """Результат collection-level обработки до декодирования и сборки артефакта."""

    raw_result: RawCollectionResult
    file_results: list[FileParseResult]


def run_collection_parse_pipeline(
    *,
    data_source: SupportsSourceFileRead,
    source_files: list[SourceFile],
    validate_raw_bytes: Callable[[bytes], object],
    parse_record: Callable[[bytes], object],
    extract_validated_chunks: Callable[..., list[bytes]],
    format_definition: SupportsTraceFormatDefinition,
    policy: str,
    pre_parse_size_warning_threshold_bytes: int,
    record_size: int,
) -> CollectionPipelineOutput:
    """Выполнить collection-level обработку и вернуть сырой результат коллекции."""

    pre_parse_estimate = estimate_pre_parse_input(
        source_files=source_files,
        record_size=record_size,
        threshold_bytes=pre_parse_size_warning_threshold_bytes,
    )
    file_results = parse_source_files_collection(
        data_source=data_source,
        source_files=source_files,
        validate_raw_bytes=validate_raw_bytes,
        parse_record=parse_record,
        extract_validated_chunks=extract_validated_chunks,
        format_definition=format_definition,
        policy=policy,
    )

    if len(file_results) == 1:
        single_result = file_results[0]
        inject_pre_parse_estimate_into_report(
            report=single_result.report,
            estimate=pre_parse_estimate,
        )
        return CollectionPipelineOutput(
            raw_result=RawCollectionResult(
                records=single_result.records,
                field_traces=single_result.field_traces,
                report=single_result.report,
            ),
            file_results=file_results,
        )

    raw_result = build_raw_collection_result(
        file_results=file_results,
    )
    inject_pre_parse_estimate_into_report(
        report=raw_result.report,
        estimate=pre_parse_estimate,
    )
    return CollectionPipelineOutput(
        raw_result=raw_result,
        file_results=file_results,
    )
