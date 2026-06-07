"""Внутренние protocol-контракты orchestration-слоя."""

from __future__ import annotations

from typing import Protocol

from ..source.data_source import SourceFile


class SupportsSourceFileRead(Protocol):
    """Внутренний контракт источника для чтения байтов одного файла."""

    def read_source_file(self, source_file: SourceFile) -> bytes:
        ...


class SupportsSourceFilesAccess(SupportsSourceFileRead, Protocol):
    """Контракт канонического доступа к файлам источника для фасадного разбора."""

    def list_source_files(self) -> list[SourceFile]:
        ...
