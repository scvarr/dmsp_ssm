"""Публичный фасад чтения и преобразования файлов DMSP SSM."""

from __future__ import annotations

from pathlib import Path

from ._internal.orchestration.reader_parse_use_case import run_reader_parse_use_case
from ._internal.validator.policy import ValidationErrorPolicy
from .parse_result import ParseResult
from .parse_options import ParseOptions

from ._internal.runtime.reader_runtime import create_reader_runtime


class Reader:
    """Публичный фасад библиотеки.

    `Reader` принимает путь к файлу или каталогу, нормализует параметры
    `ParseOptions` и передает выполнение во внутренний orchestration-сценарий.

    Ошибки некорректного использования API поднимаются как исключения.
    Ошибки и предупреждения, связанные с качеством входных данных, передаются
    через `ParseResult.report`.
    """

    def __init__(
        self,
        error_policy: str = ValidationErrorPolicy.RESYNC,
        pre_parse_size_warning_threshold_bytes: int = 256 * 1024 * 1024,
    ) -> None:
        self._default_error_policy = error_policy
        self._pre_parse_size_warning_threshold_bytes = (
            pre_parse_size_warning_threshold_bytes
        )
        self._runtime = create_reader_runtime(
            validation_error_policy=self._default_error_policy
        )

    def parse(
        self,
        path: Path | str,
        *,
        options: ParseOptions | None = None,
        recursive: bool | None = None,
        error_policy: str | None = None,
        include_missing_minute_ranges: bool | None = None,
    ) -> ParseResult:
        """Прочитать файлы DMSP SSM и вернуть результат в выбранном профиле.

        Параметры можно передать через `ParseOptions`. Именованные аргументы
        `recursive`, `error_policy` и `include_missing_minute_ranges` переопределяют
        соответствующие значения из `options`.
        """
        normalized_options = self._normalize_parse_options(
            options=options,
            recursive=recursive,
            error_policy=error_policy,
            include_missing_minute_ranges=include_missing_minute_ranges,
        )

        return run_reader_parse_use_case(
            path=path,
            options=normalized_options,
            default_error_policy=self._default_error_policy,
            runtime=self._runtime,
            output_profile=normalized_options.output_profile,
            pre_parse_size_warning_threshold_bytes=(
                self._pre_parse_size_warning_threshold_bytes
            ),
        )

    @staticmethod
    def _normalize_parse_options(
        *,
        options: ParseOptions | None,
        recursive: bool | None,
        error_policy: str | None,
        include_missing_minute_ranges: bool | None,
    ) -> ParseOptions:
        """Объединить `ParseOptions` и совместимые keyword overrides."""

        if options is None:
            base_options = ParseOptions()
        elif isinstance(options, ParseOptions):
            base_options = options
        else:
            raise TypeError(
                "Параметр options должен быть экземпляром ParseOptions или None."
            )

        return ParseOptions(
            recursive=base_options.recursive if recursive is None else recursive,
            error_policy=(
                base_options.error_policy
                if error_policy is None
                else error_policy
            ),
            include_missing_minute_ranges=(
                base_options.include_missing_minute_ranges
                if include_missing_minute_ranges is None
                else include_missing_minute_ranges
            ),
            output_profile=base_options.output_profile,
        )
