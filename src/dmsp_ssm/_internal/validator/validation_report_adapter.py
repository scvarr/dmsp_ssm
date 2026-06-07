"""Адаптеры отчета валидации для соседних внутренних этапов."""

from __future__ import annotations


def extract_validated_chunks(*, validation_report: object) -> list[bytes]:
    """Вернуть валидированные фрагменты для этапа разбора записей."""

    if hasattr(validation_report, "validated_chunks"):
        validated_chunks = getattr(validation_report, "validated_chunks")
    elif (
        isinstance(validation_report, dict)
        and "validated_chunks" in validation_report
    ):
        validated_chunks = validation_report["validated_chunks"]
    else:
        raise ValueError(
            "Результат валидации несовместим с этапом разбора: отсутствует validated_chunks."
        )

    if not isinstance(validated_chunks, list):
        raise ValueError(
            "Результат валидации несовместим с этапом разбора: validated_chunks должен быть списком bytes."
        )
    if any(not isinstance(chunk, bytes) for chunk in validated_chunks):
        raise ValueError(
            "Результат валидации несовместим с этапом разбора: validated_chunks должен быть списком bytes."
        )

    return validated_chunks


def strip_validated_chunks_for_facade(*, report: object) -> object:
    """Удалить сырые `validated_chunks` из фасадного канала отчета."""

    if isinstance(report, dict):
        report.pop("validated_chunks", None)
        return report

    if hasattr(report, "validated_chunks"):
        setattr(report, "validated_chunks", [])
    return report
