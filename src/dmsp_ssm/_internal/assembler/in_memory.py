"""Assembler итогового `ParseResult` с результатом в памяти."""

from __future__ import annotations

from .contracts import ArtifactBundle
from dmsp_ssm.parse_result import ParseResult


class InMemoryParseResultAssembler:
    """Assembler, формирующий `ParseResult` из готового `ArtifactBundle`.

    Компонент не выполняет чтение, валидацию, разбор, декодирование или построение
    выходных структур данных. Он выбирает подготовленный результат профиля и
    помещает его в `ParseResult.records`.
    """

    @staticmethod
    def assemble(bundle: ArtifactBundle) -> ParseResult:
        """Собрать `ParseResult` в памяти для поддержанных артефактов результата."""
        records = bundle.dataset
        if records is None:
            records = bundle.numpy_records
        if records is None:
            records = bundle.table_records
        if records is None:
            raise ValueError(
                "Для in-memory assembler требуется dataset, numpy_records или table_records в artifact bundle."
            )

        return ParseResult(
            records=records,
            report=bundle.report,
            metadata=bundle.metadata,
            extensions=bundle.extensions,
        )
