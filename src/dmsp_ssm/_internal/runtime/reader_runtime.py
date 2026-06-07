"""Runtime-композиция внутренних компонентов `Reader`."""

from dataclasses import dataclass

from dmsp_ssm._internal.assembler.in_memory import InMemoryParseResultAssembler
from dmsp_ssm._internal.builder.numpy_builder import NumpyBuilder
from dmsp_ssm._internal.builder.table_builder import TableBuilder
from dmsp_ssm._internal.builder.xarray_builder import XArrayBuilder
from dmsp_ssm._internal.decoder.decoder import Decoder
from dmsp_ssm._internal.format.definition import FormatDefinition
from dmsp_ssm._internal.pipeline.record_parser import RecordParser
from dmsp_ssm._internal.validator.validator import Validator


@dataclass(slots=True)
class ReaderRuntime:
    """Контейнер зависимостей, используемых сценарием `Reader.parse`.

    Runtime хранит конкретные реализации компонентов обработки:
    валидатор, parser, decoder, builders и assembler.
    """

    format_definition: dict
    validator: Validator
    record_parser: RecordParser
    decoder: Decoder
    builder: XArrayBuilder
    numpy_builder: NumpyBuilder
    table_builder: TableBuilder
    result_assembler: InMemoryParseResultAssembler

    def reset_validator(self, *, error_policy: str) -> None:
        """Пересоздать validator с новой политикой обработки ошибок."""

        self.validator = Validator(
            format_definition=self.format_definition,
            error_policy=error_policy,
        )


def create_reader_runtime(*, validation_error_policy: str) -> ReaderRuntime:
    """Создать стандартный набор runtime-компонентов для `Reader`."""

    format_definition = FormatDefinition().as_dict()

    return ReaderRuntime(
        format_definition=format_definition,
        validator=Validator(
            format_definition=format_definition,
            error_policy=validation_error_policy,
        ),
        record_parser=RecordParser(format_definition=format_definition),
        decoder=Decoder(format_definition=format_definition),
        builder=XArrayBuilder(format_definition=format_definition),
        numpy_builder=NumpyBuilder(),
        table_builder=TableBuilder(),
        result_assembler=InMemoryParseResultAssembler(),
    )
