"""Внутренний сценарий фасадного `Reader.parse`."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, cast

from dmsp_ssm.parse_options import ParseOptions
from dmsp_ssm.parse_result import ParseResult

from ..assembler.artifact_accumulator import accumulate_artifact_bundle
from ..runtime.reader_runtime import ReaderRuntime
from ..source.data_source import DataSource
from ..validator.contracts import ValidationResult
from ..validator.validation_report_adapter import (
    extract_validated_chunks,
    strip_validated_chunks_for_facade,
)
from .collection_error_policy import CollectionErrorPolicy
from .collection_pipeline import run_collection_parse_pipeline
from .missing_minutes import inject_missing_minutes_summary

ReaderOutputProfile = Literal["xarray", "numpy", "table"]


class _RuntimeFormatDefinitionAdapter:
    """Адаптер runtime-словаря формата к контракту `as_dict()`."""

    def __init__(self, definition: dict) -> None:
        self._definition = definition

    def as_dict(self) -> dict:
        return dict(self._definition)


def run_reader_parse_use_case(
    *,
    path: Path | str,
    options: ParseOptions,
    default_error_policy: str,
    runtime: ReaderRuntime,
    output_profile: ReaderOutputProfile,
    pre_parse_size_warning_threshold_bytes: int,
) -> ParseResult:
    """Выполнить внутренний сценарий `Reader.parse` и вернуть `ParseResult`."""

    active_error_policy = options.error_policy or default_error_policy
    runtime.reset_validator(error_policy=active_error_policy)

    data_source = DataSource(
        path=path,
        recursive=options.recursive,
    )
    source_files = data_source.list_source_files()
    collection_output = run_collection_parse_pipeline(
        data_source=data_source,
        source_files=source_files,
        validate_raw_bytes=runtime.validator.validate,
        parse_record=runtime.record_parser.parse_record,
        extract_validated_chunks=extract_validated_chunks,
        format_definition=_RuntimeFormatDefinitionAdapter(runtime.format_definition),
        policy=CollectionErrorPolicy.FAIL_FAST,
        pre_parse_size_warning_threshold_bytes=(
            pre_parse_size_warning_threshold_bytes
        ),
        record_size=int(runtime.format_definition["record_size"]),
    )
    raw_result = collection_output.raw_result
    facade_report_candidate = strip_validated_chunks_for_facade(
        report=raw_result.report
    )
    if isinstance(facade_report_candidate, ValidationResult):
        facade_report = facade_report_candidate
    else:
        facade_report = cast(ValidationResult, facade_report_candidate)

    artifact_bundle = accumulate_artifact_bundle(
        profile=output_profile,
        raw_records=raw_result.records,
        field_traces=raw_result.field_traces,
        report=facade_report,
        decoder=runtime.decoder,
        builder=runtime.builder,
        numpy_builder=runtime.numpy_builder,
        table_builder=runtime.table_builder,
    )
    inject_missing_minutes_summary(
        report=artifact_bundle.report,
        records=_select_summary_records_source(artifact_bundle=artifact_bundle),
        include_missing_minute_ranges=options.include_missing_minute_ranges,
        file_results=collection_output.file_results,
    )
    return runtime.result_assembler.assemble(artifact_bundle)


def _select_summary_records_source(*, artifact_bundle: object) -> object:
    """Выбрать наиболее полный доступный результат для диагностики пропусков."""

    dataset = getattr(artifact_bundle, "dataset", None)
    if dataset is not None:
        return dataset

    numpy_records = getattr(artifact_bundle, "numpy_records", None)
    if numpy_records is not None:
        return numpy_records

    decoded_records = getattr(artifact_bundle, "decoded_records", None)
    if decoded_records is not None:
        return decoded_records

    raw_records = getattr(artifact_bundle, "raw_records", None)
    if raw_records is not None:
        return raw_records

    return []
