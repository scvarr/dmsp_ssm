"""Внутренний слой управления обработкой файлов для читателя."""

from .collection_error_policy import CollectionErrorPolicy

from .file_pipeline import (
    iter_file_parse_results,
    map_source_files_to_results,
)
from .file_parse_result import FileParseResult

from .collection_result_builder import build_raw_collection_result
from .raw_collection_result import assemble_raw_collection_result
from .report_aggregation import aggregate_file_reports
from .raw_collection_result import RawCollectionResult
from .reader_parse_use_case import run_reader_parse_use_case

__all__ = [
    "CollectionErrorPolicy",
    "FileParseResult",
    "iter_file_parse_results",
    "map_source_files_to_results",
    "build_raw_collection_result",
    "assemble_raw_collection_result",
    "aggregate_file_reports",
    "RawCollectionResult",
    "run_reader_parse_use_case",
]
