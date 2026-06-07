"""Сборщик numpy-представления из декодированных записей."""

from __future__ import annotations

import numpy as np

from .contracts import (
    BuilderArtifact,
    SupportsDecodedRecordBuilder,
)
from ..pipeline.decoded_record import DecodedRecord


class NumpyBuilder(SupportsDecodedRecordBuilder):
    """Builder профиля `numpy`.

    Формирует словарь `dict[str, numpy.ndarray]` с переменными минутного и
    секундного уровней. Набор ключей и формы массивов проверяются frozen-контрактом.
    """

    REQUIRED_SECOND_LEVEL_VARS: tuple[str, str, str, str, str] = (
        "time",
        "bx",
        "by",
        "bz",
        "valid",
    )
    REQUIRED_RECORD_LEVEL_VARS: tuple[str, ...] = (
        "flight_number",
        "year",
        "day_of_year",
        "minute_start_sec_of_day",
        "latitude_deg",
        "longitude_deg",
        "altitude_km",
    )

    def build(self, records: list[DecodedRecord]) -> BuilderArtifact:
        """Построить numpy-артефакт из декодированных записей."""

        return self._build_numpy_records(records)

    @staticmethod
    def _build_numpy_records(records: list[DecodedRecord]) -> dict[str, np.ndarray]:
        """Собрать numpy-артефакт из декодированных записей."""

        record_count = len(records)
        second_count = NumpyBuilder._resolve_second_count(records)

        time = np.full((record_count, second_count), np.nan, dtype=float)
        bx = np.full((record_count, second_count), np.nan, dtype=float)
        by = np.full((record_count, second_count), np.nan, dtype=float)
        bz = np.full((record_count, second_count), np.nan, dtype=float)
        flight_number = np.zeros(record_count, dtype=int)
        year = np.zeros(record_count, dtype=int)
        day_of_year = np.zeros(record_count, dtype=int)
        minute_start_sec_of_day = np.zeros(record_count, dtype=int)
        latitude_deg = np.full(record_count, np.nan, dtype=float)
        longitude_deg = np.full(record_count, np.nan, dtype=float)
        altitude_km = np.full(record_count, np.nan, dtype=float)

        for record_index, record in enumerate(records):
            header = record.header
            footer = record.footer
            year[record_index] = int(header["year"])
            day_of_year[record_index] = int(header["day_of_year"])
            minute_start_sec_of_day[record_index] = int(
                header["first_minute_first_second_time"]
            )
            latitude_deg[record_index] = float(header["geodetic_latitude"])
            longitude_deg[record_index] = float(header["geographic_longitude"])
            altitude_km[record_index] = float(header["altitude_km"])
            flight_number[record_index] = int(footer["flight_number"])

            second_data = record.blocks.get("second_data", [])
            if len(second_data) != second_count:
                raise ValueError(
                    "Для numpy-представления все second_data должны иметь одинаковую длину."
                )
            for second_position, point in enumerate(second_data):
                time[record_index, second_position] = float(point["time"])
                bx[record_index, second_position] = float(point["bx"])
                by[record_index, second_position] = float(point["by"])
                bz[record_index, second_position] = float(point["bz"])

        missing_second_mask = time == -1000.0
        valid = ~missing_second_mask
        time[missing_second_mask] = np.nan
        bx[missing_second_mask] = np.nan
        by[missing_second_mask] = np.nan
        bz[missing_second_mask] = np.nan

        numpy_records: dict[str, np.ndarray] = {
            "time": time,
            "bx": bx,
            "by": by,
            "bz": bz,
            "valid": valid,
            "flight_number": flight_number,
            "year": year,
            "day_of_year": day_of_year,
            "minute_start_sec_of_day": minute_start_sec_of_day,
            "latitude_deg": latitude_deg,
            "longitude_deg": longitude_deg,
            "altitude_km": altitude_km,
        }
        NumpyBuilder._assert_frozen_contract(
            numpy_records=numpy_records,
            record_count=record_count,
            second_count=second_count,
        )
        return numpy_records

    @staticmethod
    def _resolve_second_count(records: list[DecodedRecord]) -> int:
        """Определить число секундных элементов по первой записи."""

        if not records:
            return 0
        first_block = records[0].blocks.get("second_data", [])
        return len(first_block)

    @staticmethod
    def _assert_frozen_contract(
        *,
        numpy_records: dict[str, np.ndarray],
        record_count: int,
        second_count: int,
    ) -> None:
        """Проверить, что сборщик возвращает зафиксированный набор ключей и форм."""

        expected_keys = set(NumpyBuilder.REQUIRED_SECOND_LEVEL_VARS) | set(
            NumpyBuilder.REQUIRED_RECORD_LEVEL_VARS
        )
        if set(numpy_records) != expected_keys:
            raise ValueError("Нарушен зафиксированный контракт сборщика numpy: keys.")

        second_level_shape = (record_count, second_count)
        record_level_shape = (record_count,)
        for key in NumpyBuilder.REQUIRED_SECOND_LEVEL_VARS:
            if numpy_records[key].shape != second_level_shape:
                raise ValueError("Нарушен зафиксированный контракт сборщика numpy: shape.")
        for key in NumpyBuilder.REQUIRED_RECORD_LEVEL_VARS:
            if numpy_records[key].shape != record_level_shape:
                raise ValueError("Нарушен зафиксированный контракт сборщика numpy: shape.")
