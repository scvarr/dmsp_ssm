"""Внутренние контрактные границы слоя финальной сборки результата.

Assembler-слой расположен после подготовки выходного артефакта и отвечает за
преобразование `ArtifactBundle` в фасадный `ParseResult`.

Слой не выполняет чтение, валидацию, разбор, декодирование или построение
выходных структур данных. Он получает уже подготовленные артефакты для
публичных профилей `xarray`, `numpy` и `table`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

import numpy as np
import xarray as xr

from ..pipeline.decoded_record import DecodedRecord
from ..pipeline.field_trace import FieldTrace
from ..pipeline.raw_record import RawRecord
from dmsp_ssm.parse_result import ParseResult
from ..validator.contracts import ValidationResult

OutputProfile = Literal["raw", "decoded", "xarray", "numpy", "table"]


@dataclass(slots=True, frozen=True)
class ProfileArtifactRequirements:
    """Описание артефактов, необходимых для выбранного профиля вывода.

    Используется внутренним accumulation-слоем, чтобы подготовить только те данные,
    которые требуются для сборки результата выбранного профиля.
    """

    required_artifacts: frozenset[str]


OUTPUT_PROFILE_ARTIFACT_REQUIREMENTS: dict[
    OutputProfile,
    ProfileArtifactRequirements,
] = {
    "raw": ProfileArtifactRequirements(
        required_artifacts=frozenset({"raw_records"})
    ),
    "decoded": ProfileArtifactRequirements(
        required_artifacts=frozenset({"decoded_records"})
    ),
    "xarray": ProfileArtifactRequirements(
        required_artifacts=frozenset({"dataset"})
    ),
    "numpy": ProfileArtifactRequirements(
        required_artifacts=frozenset({"numpy_records"})
    ),
    "table": ProfileArtifactRequirements(
        required_artifacts=frozenset({"table_records"})
    ),
}


@dataclass(slots=True)
class ArtifactBundle:
    """Внутренний контейнер артефактов между use-case и assembler-слоем.

    `ArtifactBundle` переносит диагностический отчет, подготовленный результат
    выбранного профиля и дополнительные служебные данные. Контейнер не является
    публичным API и не задает потоковый протокол обработки.

    Необязательные поля отсутствуют, если соответствующий артефакт не требуется
    для выбранного профиля вывода.
    """

    report: ValidationResult
    raw_records: list[RawRecord] | None = None
    decoded_records: list[DecodedRecord] | None = None
    dataset: xr.Dataset | None = None
    numpy_records: dict[str, np.ndarray] | None = None
    table_records: list[dict[str, object]] | None = None
    field_traces: list[FieldTrace] | None = None
    metadata: dict[str, object] | None = None
    extensions: dict[str, object] | None = None


class SupportsParseResultAssembler(Protocol):
    """Контракт assembler-компонента для сборки фасадного `ParseResult`."""

    def assemble(self, bundle: ArtifactBundle) -> ParseResult:
        """Собрать фасадный результат без чтения, декодирования и построения артефактов."""
