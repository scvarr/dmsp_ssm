"""Сборщик table-профиля из `FieldTrace` и декодированных записей."""

from __future__ import annotations

from ..pipeline.decoded_record import DecodedRecord
from ..pipeline.field_trace import FieldTrace


class TableBuilder:
    """Builder профиля `table`.

    Формирует long-format trace-представление, где каждая строка описывает одно
    поле записи и связывает raw-значение с decoded/normalized значениями.
    """

    _RECORD_LEVEL_FIELD_SOURCES: dict[str, tuple[tuple[str, str], ...]] = {
        "year": (("header", "year"),),
        "day_of_year": (("header", "day_of_year"),),
        "minute_start_sec_of_day": (
            ("header", "minute_start_sec_of_day"),
            ("header", "first_minute_first_second_time"),
        ),
        "first_minute_first_second_time": (
            ("header", "minute_start_sec_of_day"),
            ("header", "first_minute_first_second_time"),
        ),
        "latitude_deg": (
            ("header", "latitude_deg"),
            ("header", "geodetic_latitude"),
        ),
        "geodetic_latitude": (
            ("header", "latitude_deg"),
            ("header", "geodetic_latitude"),
        ),
        "longitude_deg": (
            ("header", "longitude_deg"),
            ("header", "geographic_longitude"),
        ),
        "geographic_longitude": (
            ("header", "longitude_deg"),
            ("header", "geographic_longitude"),
        ),
        "altitude_km": (
            ("header", "altitude_km"),
            ("header", "altitude"),
        ),
        "altitude": (
            ("header", "altitude_km"),
            ("header", "altitude"),
        ),
        "flight_number": (("footer", "flight_number"),),
    }
    _MISSING_SENSITIVE_SECOND_FIELDS: frozenset[str] = frozenset(
        {"time", "bx", "by", "bz"}
    )

    def build(
        self,
        *,
        field_traces: list[FieldTrace],
        decoded_records: list[DecodedRecord] | None = None,
    ) -> list[dict[str, object]]:
        """Построить table-строки из trace-данных в детерминированном порядке."""

        rows: list[dict[str, object]] = []
        for trace in field_traces:
            if decoded_records is None:
                decoded_value = None
                normalized_value = None
                valid = True
            else:
                decoded_value = self._resolve_decoded_value(
                    trace=trace,
                    decoded_records=decoded_records,
                )
                normalized_value, valid = self._resolve_normalized_and_valid(
                    trace=trace,
                    decoded_value=decoded_value,
                    decoded_records=decoded_records,
                )
            rows.append(
                {
                    "record_index": trace.record_index,
                    "second_index": trace.second_index,
                    "section": trace.section,
                    "field_name": trace.field_name,
                    "field_role": trace.field_role,
                    "byte_offset": trace.byte_offset,
                    "byte_length": trace.byte_length,
                    "raw_hex": trace.raw_hex,
                    "raw_int": trace.raw_int,
                    "decoded_value": decoded_value,
                    "normalized_value": normalized_value,
                    "unit": trace.unit,
                    "transform": trace.transform,
                    "valid": valid,
                }
            )
        return rows

    @classmethod
    def _resolve_normalized_and_valid(
        cls,
        *,
        trace: FieldTrace,
        decoded_value: int | float | str | None,
        decoded_records: list[DecodedRecord],
    ) -> tuple[int | float | str | None, bool]:
        """Определить `normalized_value` и `valid` для table-строки."""

        if trace.second_index is None:
            return decoded_value, True
        if decoded_value is None:
            return None, True
        if trace.field_name not in cls._MISSING_SENSITIVE_SECOND_FIELDS:
            return decoded_value, True

        missing_second = cls._is_missing_second(
            decoded_records=decoded_records,
            record_index=trace.record_index,
            second_index=trace.second_index,
        )
        if missing_second is True:
            return None, False
        return decoded_value, True

    @classmethod
    def _resolve_decoded_value(
        cls,
        *,
        trace: FieldTrace,
        decoded_records: list[DecodedRecord] | None,
    ) -> int | float | str | None:
        """Сопоставить trace со значением из decoded-слоя, если оно доступно."""

        if decoded_records is None:
            return None
        if trace.record_index < 0 or trace.record_index >= len(decoded_records):
            return None

        decoded_record = decoded_records[trace.record_index]
        if trace.second_index is None:
            return cls._resolve_record_level_value(
                decoded_record=decoded_record,
                field_name=trace.field_name,
            )
        return cls._resolve_second_level_value(
            decoded_record=decoded_record,
            second_index=trace.second_index,
            field_name=trace.field_name,
        )

    @classmethod
    def _resolve_record_level_value(
        cls,
        *,
        decoded_record: DecodedRecord,
        field_name: str,
    ) -> int | float | str | None:
        """Получить значение record-level поля из `header` или `footer`."""

        sources = cls._RECORD_LEVEL_FIELD_SOURCES.get(field_name)
        if sources is None:
            return None
        for section_name, source_field_name in sources:
            if section_name == "header" and source_field_name in decoded_record.header:
                return decoded_record.header.get(source_field_name)
            if section_name == "footer" and source_field_name in decoded_record.footer:
                return decoded_record.footer.get(source_field_name)
        return None

    @staticmethod
    def _resolve_second_level_value(
        *,
        decoded_record: DecodedRecord,
        second_index: int | None,
        field_name: str,
    ) -> int | float | str | None:
        """Получить значение second-level поля из блока `second_data`."""

        if second_index is None:
            return None
        second_data = decoded_record.blocks.get("second_data", [])
        if second_index < 0 or second_index >= len(second_data):
            return None
        return second_data[second_index].get(field_name)

    @staticmethod
    def _is_missing_second(
        *,
        decoded_records: list[DecodedRecord],
        record_index: int,
        second_index: int | None,
    ) -> bool | None:
        """Проверить missing second по `time == -1000.0`, если данные доступны."""

        if second_index is None:
            return None
        if record_index < 0 or record_index >= len(decoded_records):
            return None
        second_data = decoded_records[record_index].blocks.get("second_data", [])
        if second_index < 0 or second_index >= len(second_data):
            return None

        time_value = second_data[second_index].get("time")
        if time_value is None:
            return None
        try:
            return float(time_value) == -1000.0
        except (TypeError, ValueError):
            return None
