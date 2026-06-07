"""Внутренние контракты builder-слоя."""

from __future__ import annotations

from typing import Protocol

from ..pipeline.decoded_record import DecodedRecord


class BuilderArtifact(Protocol):
    """Маркерный контракт результата builder-компонента."""


class SupportsDecodedRecordBuilder(Protocol):
    """Контракт builder-компонента, работающего с декодированными записями."""

    def build(self, records: list[DecodedRecord]) -> BuilderArtifact:
        """Построить выходной артефакт из декодированных записей."""
