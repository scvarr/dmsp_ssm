"""Валидация бинарного потока DMSP SSM по описанию формата."""

from __future__ import annotations

from typing import Any, Literal, cast

from ..format.definition_validator import FormatDefinitionValidator
from ..format.raw_field_reader import BinaryFieldReader
from .contracts import (
    ValidationIncident,
    ValidationRecordContext,
    ValidationResult,
)
from .field_resolver import ValidationFieldResolver
from .policy import ValidationErrorPolicy


class Validator:
    """Валидация raw-потока по обязательным полям формата DMSP SSM."""

    INVALID_RECORD_MESSAGE = "Запись не содержит валидные обязательные поля"
    TRAILING_BYTES_MESSAGE = "В конце потока обнаружен неполный фрагмент записи"
    DESYNC_MESSAGE = "Потеря доверия к текущей границе записи, требуется повторная синхронизация"
    RESYNC_CONFIRMATION_RECORDS = 2

    def __init__(
        self,
        *,
        format_definition: dict[str, Any],
        error_policy: str = ValidationErrorPolicy.STRICT,
    ) -> None:
        if error_policy not in ValidationErrorPolicy.ALL:
            raise ValueError(f"Недопустимая политика обработки ошибок: {error_policy}")

        FormatDefinitionValidator().validate(format_definition)

        self.error_policy = error_policy
        self._format_definition = format_definition

        self.record_size = int(format_definition["record_size"])
        byte_order = format_definition["byte_order"]
        if byte_order not in ("little", "big"):
            raise ValueError(
                f"Недопустимый byte_order в формате: {byte_order!r}"
            )
        self.byte_order: Literal["little", "big"] = cast(
            Literal["little", "big"],
            byte_order,
        )
        field_resolver = ValidationFieldResolver(
            format_definition=format_definition
        )
        self.field_definitions = field_resolver.field_definitions
        self.validation_field_definitions = field_resolver.resolve()
        self.validation_fields = list(self.validation_field_definitions)
        self._raw_field_reader = BinaryFieldReader(byte_order=self.byte_order)

    def validate(self, raw_bytes: bytes) -> ValidationResult:
        """Проверить raw-поток и вернуть `ValidationResult`.

        ``validated_chunks` используются для передачи валидных записей на этап разбора.
        Перед возвратом фасадного результата они удаляются из `ParseResult.report`.
        """

        incidents: list[ValidationIncident] = []
        validated_chunks: list[bytes] = []
        summary: dict[str, Any] = {}

        full_record_count = len(raw_bytes) // self.record_size
        trailing_byte_count = len(raw_bytes) % self.record_size
        full_stream_size = full_record_count * self.record_size

        summary["candidate_record_count"] = full_record_count

        status = "ok"
        offset = 0
        consecutive_invalid_records = 0
        last_valid_context: ValidationRecordContext | None = None

        while offset < full_stream_size:
            record = raw_bytes[offset:offset + self.record_size]

            if self._is_valid_record(record):
                consecutive_invalid_records = 0
                validated_chunks.append(record)
                last_valid_context = self._build_record_context(record=record, offset=offset)
                offset += self.record_size
                continue

            consecutive_invalid_records += 1

            if self.error_policy == ValidationErrorPolicy.STRICT:
                incidents.append(
                    self._invalid_record_incident(
                        offset,
                        previous_context=last_valid_context,
                        next_context=self._find_next_valid_context_on_trusted_grid(
                            raw_bytes=raw_bytes,
                            start_offset=offset + self.record_size,
                            limit_offset=full_stream_size - self.record_size,
                        ),
                    )
                )
                status = "error"
                break

            if self.error_policy == ValidationErrorPolicy.RESYNC:
                next_boundary = self._find_next_valid_boundary(
                    raw_bytes=raw_bytes,
                    start_offset=offset + 1,
                    limit_offset=len(raw_bytes) - self.record_size,
                )

                if next_boundary is not None:
                    incidents.append(
                        self._desync_incident(
                            start_offset=offset,
                            end_offset=next_boundary,
                            previous_context=last_valid_context,
                            next_context=self._build_valid_context_at_offset(
                                raw_bytes=raw_bytes,
                                offset=next_boundary,
                            ),
                        )
                    )
                    consecutive_invalid_records = 0
                    offset = next_boundary
                    continue

                if consecutive_invalid_records == 1:
                    incidents.append(
                        self._invalid_record_incident(
                            offset,
                            previous_context=last_valid_context,
                            next_context=self._find_next_valid_context_on_trusted_grid(
                                raw_bytes=raw_bytes,
                                start_offset=offset + self.record_size,
                                limit_offset=full_stream_size - self.record_size,
                            ),
                        )
                    )
                    offset += self.record_size
                    continue

                incidents.append(
                    self._desync_incident(
                        start_offset=offset - self.record_size,
                        end_offset=len(raw_bytes),
                        previous_context=last_valid_context,
                        next_context=None,
                    )
                )
                status = "error"
                break

        if trailing_byte_count > 0 and status == "ok":
            incidents.append(
                self._trailing_bytes_incident(
                    start_offset=full_stream_size,
                    end_offset=len(raw_bytes),
                )
            )

            if self.error_policy == ValidationErrorPolicy.STRICT:
                status = "error"

        return ValidationResult(
            status=status,
            outcome=self._derive_outcome(status=status),
            validated_chunks=validated_chunks,
            incidents=incidents,
            summary=summary,
        )

    def _is_valid_record(self, record: bytes) -> bool:
        """Проверить обязательные поля одной записи по диапазонам."""
        for field_name in self.validation_fields:
            field = self.validation_field_definitions[field_name]
            value = self._raw_field_reader.read_raw_int(
                record=record,
                field_definition=field,
            )

            if "min" in field and value < field["min"]:
                return False
            if "max" in field and value > field["max"]:
                return False

        return True

    def _invalid_record_incident(
        self,
        offset: int,
        *,
        previous_context: ValidationRecordContext | None = None,
        next_context: ValidationRecordContext | None = None,
    ) -> ValidationIncident:
        """Сформировать инцидент локальной ошибки на доверенной границе."""
        return ValidationIncident(
            kind="invalid_record",
            start_offset=offset,
            end_offset=offset + self.record_size,
            message=self.INVALID_RECORD_MESSAGE,
            previous_context=previous_context,
            next_context=next_context,
            estimated_missing_records=self._estimate_missing_records(
                previous_context=previous_context,
                next_context=next_context,
            ),
        )

    def _desync_incident(
        self,
        *,
        start_offset: int,
        end_offset: int,
        previous_context: ValidationRecordContext | None = None,
        next_context: ValidationRecordContext | None = None,
    ) -> ValidationIncident:
        """Сформировать инцидент потери доверия к границе записи."""
        return ValidationIncident(
            kind="desync",
            start_offset=start_offset,
            end_offset=end_offset,
            message=self.DESYNC_MESSAGE,
            previous_context=previous_context,
            next_context=next_context,
            estimated_missing_records=self._estimate_missing_records(
                previous_context=previous_context,
                next_context=next_context,
            ),
        )

    def _trailing_bytes_incident(
        self,
        *,
        start_offset: int,
        end_offset: int,
    ) -> ValidationIncident:
        """Сформировать инцидент неполного хвоста в конце потока."""
        return ValidationIncident(
            kind="trailing_bytes",
            start_offset=start_offset,
            end_offset=end_offset,
            message=self.TRAILING_BYTES_MESSAGE,
        )

    def _find_next_valid_boundary(
        self,
        *,
        raw_bytes: bytes,
        start_offset: int,
        limit_offset: int,
    ) -> int | None:
        """Найти следующую валидную границу записи в пределах окна поиска."""
        for candidate_offset in range(start_offset, limit_offset + 1):
            if self._is_confirmed_boundary(
                raw_bytes=raw_bytes,
                offset=candidate_offset,
            ):
                return candidate_offset
        return None

    def _is_confirmed_boundary(
        self,
        *,
        raw_bytes: bytes,
        offset: int,
    ) -> bool:
        """Проверить новую границу подряд валидными записями."""
        for index in range(self.RESYNC_CONFIRMATION_RECORDS):
            candidate_offset = offset + (index * self.record_size)
            if not self._is_valid_record_at_offset(
                raw_bytes=raw_bytes,
                offset=candidate_offset,
            ):
                return False
        return True

    def _is_valid_record_at_offset(
        self,
        *,
        raw_bytes: bytes,
        offset: int,
    ) -> bool:
        """Проверить валидность записи, начиная с заданного смещения."""
        end_offset = offset + self.record_size

        if end_offset > len(raw_bytes):
            return False

        record = raw_bytes[offset:end_offset]
        return self._is_valid_record(record)

    def _build_record_context(
        self,
        *,
        record: bytes,
        offset: int,
    ) -> ValidationRecordContext:
        """Собрать контекст валидной записи для инцидента."""
        values: dict[str, int] = {}
        for field_name in self.validation_fields:
            field = self.validation_field_definitions[field_name]
            values[field_name] = self._raw_field_reader.read_raw_int(
                record=record,
                field_definition=field,
            )
        return {
            "offset": offset,
            "validation_fields": values,
        }

    def _build_valid_context_at_offset(
        self,
        *,
        raw_bytes: bytes,
        offset: int,
    ) -> ValidationRecordContext | None:
        """Вернуть контекст, если запись по offset валидна."""
        if not self._is_valid_record_at_offset(raw_bytes=raw_bytes, offset=offset):
            return None

        end_offset = offset + self.record_size
        record = raw_bytes[offset:end_offset]
        return self._build_record_context(record=record, offset=offset)

    def _find_next_valid_context_on_trusted_grid(
        self,
        *,
        raw_bytes: bytes,
        start_offset: int,
        limit_offset: int,
    ) -> ValidationRecordContext | None:
        """Найти следующую валидную запись на текущей доверенной сетке."""
        if start_offset > limit_offset:
            return None

        for candidate_offset in range(start_offset, limit_offset + 1, self.record_size):
            context = self._build_valid_context_at_offset(
                raw_bytes=raw_bytes,
                offset=candidate_offset,
            )
            if context is not None:
                return context
        return None

    @staticmethod
    def _extract_position_from_context(
        context: ValidationRecordContext,
    ) -> tuple[int, int] | None:
        """Вернуть (year, absolute_minute) из контекста, если хватает данных."""
        validation_fields = context["validation_fields"]
        if "year" not in validation_fields:
            return None
        if "day_of_year" not in validation_fields:
            return None
        if "flight_number" not in validation_fields:
            return None

        year = validation_fields["year"]
        absolute_minute = (
            validation_fields["day_of_year"] * 1440
            + validation_fields["flight_number"]
        )
        return year, absolute_minute

    def _estimate_missing_records(
        self,
        *,
        previous_context: ValidationRecordContext | None,
        next_context: ValidationRecordContext | None,
    ) -> int | None:
        """Оценить число потерянных записей между соседними валидными точками."""
        if previous_context is None or next_context is None:
            return None

        previous_position = self._extract_position_from_context(previous_context)
        next_position = self._extract_position_from_context(next_context)
        if previous_position is None or next_position is None:
            return None

        previous_year, previous_absolute_minute = previous_position
        next_year, next_absolute_minute = next_position
        if previous_year != next_year:
            return None

        return max(0, next_absolute_minute - previous_absolute_minute - 1)

    @staticmethod
    def _derive_outcome(*, status: str) -> Literal["fatal", "nonfatal"]:
        """Определить, является ли результат фатальным."""
        return "fatal" if status == "error" else "nonfatal"
