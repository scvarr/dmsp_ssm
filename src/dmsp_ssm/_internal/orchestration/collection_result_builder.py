"""Сборка сырого результата коллекции файлов."""

from __future__ import annotations

from .file_parse_result import FileParseResult
from .raw_collection_result import RawCollectionResult, assemble_raw_collection_result


def build_raw_collection_result(
    *,
    file_results: list[FileParseResult],
) -> RawCollectionResult:
    """Собрать `RawCollectionResult` из file-level результатов."""
    return assemble_raw_collection_result(file_results)
