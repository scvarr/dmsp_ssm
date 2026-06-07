"""Накопление артефактов результата по выбранному профилю вывода."""

from __future__ import annotations

from typing import Literal

from dmsp_ssm._internal.assembler.contracts import (
    ArtifactBundle,
    OUTPUT_PROFILE_ARTIFACT_REQUIREMENTS
)

from ..builder.numpy_builder import NumpyBuilder
from ..builder.table_builder import TableBuilder
from ..builder.xarray_builder import XArrayBuilder
from ..decoder.decoder import Decoder
from ..pipeline.decoded_record import DecodedRecord
from ..pipeline.field_trace import FieldTrace
from ..pipeline.raw_record import RawRecord
from ..validator.contracts import ValidationResult

ReaderOutputProfile = Literal["raw", "decoded", "xarray", "numpy", "table"]


def accumulate_artifact_bundle(
        *,
        profile: ReaderOutputProfile,
        raw_records: list[RawRecord],
        field_traces: list[FieldTrace] | None,
        report: ValidationResult,
        decoder: Decoder,
        builder: XArrayBuilder,
        numpy_builder: NumpyBuilder,
        table_builder: TableBuilder | None = None,
) -> ArtifactBundle:
    """Собрать `ArtifactBundle` из артефактов, требуемых выбранным профилем."""

    requirements = OUTPUT_PROFILE_ARTIFACT_REQUIREMENTS.get(profile)
    if requirements is None:
        raise ValueError(f"Неподдерживаемый внутренний профиль вывода: {profile}")

    bundle = ArtifactBundle(
        report=report,
        field_traces=field_traces,
    )
    required_artifacts = requirements.required_artifacts

    decoded_records: list[DecodedRecord] | None = None

    if "raw_records" in required_artifacts:
        bundle.raw_records = raw_records

    if (
            "decoded_records" in required_artifacts
            or "dataset" in required_artifacts
            or "numpy_records" in required_artifacts
    ):
        decoded_records = [decoder.decode(record) for record in raw_records]

    if "decoded_records" in required_artifacts:
        bundle.decoded_records = decoded_records

    if "dataset" in required_artifacts:
        bundle.dataset = builder.build(decoded_records or [])

    if "numpy_records" in required_artifacts:
        bundle.numpy_records = numpy_builder.build(decoded_records or [])

    if "table_records" in required_artifacts:
        if table_builder is None:
            raise ValueError(
                "Для internal profile 'table' требуется table_builder."
            )
        if decoded_records is None:
            decoded_records = [decoder.decode(record) for record in raw_records]
        bundle.decoded_records = decoded_records
        bundle.table_records = table_builder.build(
            field_traces=field_traces or [],
            decoded_records=decoded_records,
        )

    return bundle
