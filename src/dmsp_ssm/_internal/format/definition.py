"""Каноническое внутреннее описание бинарного формата DMSP SSM."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


class FormatDefinition:
    """Контейнер описания структуры минутной записи DMSP SSM."""

    _FORMAT_DEFINITION: dict[str, Any] = {
        "format_name": "dmsp_ssm_minute_record",
        "record_size": 988,
        "byte_order": "big",
        "validation_fields": [
            "year",
            "day_of_year",
        ],
        "header": [
            {
                "name": "year",
                "offset": 0,
                "size": 4,
                "type": "int",
                "min": 1987,
                "max": 2049,
                "unit": "year",
            },
            {
                "name": "day_of_year",
                "offset": 4,
                "size": 4,
                "type": "int",
                "min": 1,
                "max": 366,
                "unit": "day",
            },
            {
                "name": "first_minute_first_second_time",
                "offset": 8,
                "size": 4,
                "type": "int",
                "min": 0,
                "max": 86400,
                "transform": "float(i)/1000.0",
                "unit": "s",
            },
            {
                "name": "geodetic_latitude",
                "offset": 12,
                "size": 4,
                "type": "int",
                "min": 0,
                "max": 18000,
                "transform": "(float(i)/100.0)-90.0",
                "unit": "degree",
            },
            {
                "name": "geographic_longitude",
                "offset": 16,
                "size": 4,
                "type": "int",
                "min": 0,
                "max": 36000,
                "transform": "float(i)/100.0",
                "unit": "degree",
            },
            {
                "name": "altitude_km",
                "offset": 20,
                "size": 4,
                "type": "int",
                "transform": "float(i)/10.0",
                "unit": "km",
            },
        ],
        "blocks": [
            {
                "name": "second_data",
                "repeat": 60,
                "stride": 16,
                "start_offset": 24,
                "fields": [
                    {
                        "name": "time",
                        "offset": 0,
                        "size": 4,
                        "type": "int",
                        "min": 0,
                        "max": 86400,
                        "transform": "float(i)/1000.0",
                        "unit": "s",
                    },
                    {
                        "name": "bx",
                        "offset": 4,
                        "size": 4,
                        "type": "int",
                        "unit": "nT",
                    },
                    {
                        "name": "by",
                        "offset": 8,
                        "size": 4,
                        "type": "int",
                        "unit": "nT",
                    },
                    {
                        "name": "bz",
                        "offset": 12,
                        "size": 4,
                        "type": "int",
                        "unit": "nT",
                    },
                ],
            },
        ],
        "footer": [
            {
                "name": "flight_number",
                "offset": 984,
                "size": 4,
                "type": "int",
                "min": 6,
                "max": 20,
                "unit": "1",
            },
        ],
    }

    def as_dict(self) -> dict[str, Any]:
        """Вернуть независимую копию описания формата."""
        return deepcopy(self._FORMAT_DEFINITION)
