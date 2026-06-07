"""Сборщик xarray-представления из декодированных записей."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import xarray as xr

from .contracts import (
    BuilderArtifact,
    SupportsDecodedRecordBuilder,
)
from ..pipeline.decoded_record import DecodedRecord


@dataclass(slots=True, frozen=True)
class XArrayDimensionModel:
    """Модель размерностей выходного `xarray.Dataset`.

    Размерность `record` соответствует минутной записи, а `second` — элементу
    повторяющегося блока `second_data` внутри этой записи. Раздельные размерности
    сохраняют исходную структуру формата и не схлопывают секундные измерения в
    одну плоскую временную ось.
    """

    dimensions: tuple[str, str] = ("record", "second")
    coordinates: tuple[str, str] = ("record_time", "second_index")
    data_variables: tuple[str, str, str] = ("bx", "by", "bz")

    @staticmethod
    def coordinate_dimensions(coordinate_name: str) -> tuple[str, ...]:
        """Вернуть размерности координаты в минимальной модели."""

        mapping = {
            "record_time": ("record",),
            "second_index": ("second",),
        }
        return mapping[coordinate_name]

    @staticmethod
    def data_variable_dimensions(variable_name: str) -> tuple[str, ...]:
        """Вернуть размерности переменной данных в минимальной модели."""

        mapping = {
            "bx": ("record", "second"),
            "by": ("record", "second"),
            "bz": ("record", "second"),
        }
        return mapping[variable_name]


class XArrayBuilder(SupportsDecodedRecordBuilder):
    """Builder профиля `xarray`.

    Формирует `xarray.Dataset` с двумя размерностями: `record` и `second`.

    Контракт результата:
    - dims: `record`, `second`;
    - coords: `record_time`, `second_index`;
    - переменные секундного уровня: `time`, `bx`, `by`, `bz`, `valid`;
    - переменные уровня записи: `flight_number`, `year`, `day_of_year`,
      `minute_start_sec_of_day`, `latitude_deg`, `longitude_deg`, `altitude_km`;
    - attrs: `builder`, `pipeline_terminal_stage`, `record_dimension`, `second_dimension`.

    Пропущенные секундные измерения определяются по `time == -1000.0`.
    Для таких позиций `time`, `bx`, `by` и `bz` нормализуются в `NaN`,
    а `valid` принимает значение `False`.
    """

    REQUIRED_DIMS: tuple[str, str] = ("record", "second")
    REQUIRED_COORDS: tuple[str, str] = ("record_time", "second_index")
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
    REQUIRED_ATTRS: tuple[str, str, str, str] = (
        "builder",
        "pipeline_terminal_stage",
        "record_dimension",
        "second_dimension",
    )
    FIELD_NAME_ALIASES: dict[str, str] = {
        "first_minute_first_second_time": "minute_start_sec_of_day",
        "geodetic_latitude": "latitude_deg",
        "geographic_longitude": "longitude_deg",
    }

    def __init__(self, *, format_definition: dict[str, Any] | None = None) -> None:
        self._format_definition = (
            deepcopy(format_definition)
            if format_definition is not None
            else None
        )

    def build(self, records: list[DecodedRecord]) -> BuilderArtifact:
        """Построить `xarray.Dataset` из декодированных записей."""

        dataset = self._build_minimal_dataset(records)
        self._apply_units(dataset)
        XArrayBuilder._assert_frozen_contract(dataset)
        return dataset

    @staticmethod
    def _build_minimal_dataset(records: list[DecodedRecord]) -> xr.Dataset:
        """Собрать `xarray.Dataset` по зафиксированной модели размерностей."""

        record_count = len(records)
        second_count = XArrayBuilder._resolve_second_count(records)

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
        record_time = [XArrayBuilder._extract_record_time(record) for record in records]
        second_index = list(range(second_count))

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
                    "Для минимального xarray Dataset все second_data должны иметь одинаковую длину."
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

        dataset = xr.Dataset(
            data_vars={
                "valid": (("record", "second"), valid),
                "time": (("record", "second"), time),
                "bx": (("record", "second"), bx),
                "by": (("record", "second"), by),
                "bz": (("record", "second"), bz),
                "flight_number": (("record",), flight_number),
                "year": (("record",), year),
                "day_of_year": (("record",), day_of_year),
                "minute_start_sec_of_day": (("record",), minute_start_sec_of_day),
                "latitude_deg": (("record",), latitude_deg),
                "longitude_deg": (("record",), longitude_deg),
                "altitude_km": (("record",), altitude_km),
            },
            coords={
                "record_time": ("record", np.array(record_time, dtype="datetime64[s]")),
                "second_index": ("second", second_index),
            },
        )
        dataset.attrs.update(
            {
                "builder": "xarray",
                "pipeline_terminal_stage": "builder",
                "record_dimension": "record",
                "second_dimension": "second",
            }
        )
        return dataset

    def _apply_units(self, dataset: xr.Dataset) -> None:
        """Добавить единицы измерения к переменным dataset из описания формата."""

        if self._format_definition is None:
            return
        for variable_name, unit in self._build_units_map().items():
            if variable_name in dataset:
                dataset[variable_name].attrs["units"] = unit

    def _build_units_map(self) -> dict[str, str]:
        """Построить карту единиц для имен переменных xarray."""

        if self._format_definition is None:
            return {}

        units_by_variable: dict[str, str] = {}
        for field_definition in self._iter_format_fields(self._format_definition):
            field_name = str(field_definition.get("name"))
            unit = field_definition.get("unit")
            if unit is None:
                continue
            variable_name = self.FIELD_NAME_ALIASES.get(field_name, field_name)
            units_by_variable[variable_name] = str(unit)
        return units_by_variable

    @staticmethod
    def _iter_format_fields(
        format_definition: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Вернуть плоский список описаний полей из описания формата."""

        fields: list[dict[str, Any]] = []
        fields.extend(format_definition.get("header", []))
        for block_definition in format_definition.get("blocks", []):
            fields.extend(block_definition.get("fields", []))
        fields.extend(format_definition.get("footer", []))
        return fields

    @staticmethod
    def _resolve_second_count(records: list[DecodedRecord]) -> int:
        """Определить число секундных элементов по первой записи."""

        if not records:
            return 0
        first_block = records[0].blocks.get("second_data", [])
        return len(first_block)

    @staticmethod
    def _extract_record_time(record: DecodedRecord) -> datetime:
        """Собрать `record_time` из декодированных временных полей записи."""

        year = int(record.header["year"])
        day_of_year = int(record.header["day_of_year"])
        first_second_time = int(record.header["first_minute_first_second_time"])
        day_start = datetime(year, 1, 1) + timedelta(days=day_of_year - 1)
        return day_start + timedelta(seconds=first_second_time)

    @staticmethod
    def _assert_frozen_contract(dataset: xr.Dataset) -> None:
        """Проверить соответствие результата зафиксированному контракту dataset."""

        expected_data_vars = set(XArrayBuilder.REQUIRED_SECOND_LEVEL_VARS) | set(
            XArrayBuilder.REQUIRED_RECORD_LEVEL_VARS
        )
        if set(dataset.dims) != set(XArrayBuilder.REQUIRED_DIMS):
            raise ValueError("Нарушен зафиксированный контракт сборщика xarray: dims.")
        if set(dataset.coords) != set(XArrayBuilder.REQUIRED_COORDS):
            raise ValueError("Нарушен зафиксированный контракт сборщика xarray: coords.")
        if set(dataset.data_vars) != expected_data_vars:
            raise ValueError("Нарушен зафиксированный контракт сборщика xarray: data_vars.")
        if set(dataset.attrs) != set(XArrayBuilder.REQUIRED_ATTRS):
            raise ValueError("Нарушен зафиксированный контракт сборщика xarray: attrs.")
