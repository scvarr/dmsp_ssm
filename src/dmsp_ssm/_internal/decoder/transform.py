"""Применение transform-выражений на этапе декодирования."""

from __future__ import annotations

from typing import Any


def apply_transform(raw_value: int, field_definition: dict[str, Any]) -> int | float:
    """Применить правило преобразования к одному raw-значению.

    Если в описании поля отсутствует `transform`, возвращается исходное значение.
    Если `transform` задан, выражение вычисляется в ограниченном контексте с
    переменной `i`, содержащей raw-значение.

    Ошибки вычисления преобразуются в `ValueError`. Диагностический отчет на этом
    слое не формируется.
    """

    transform = field_definition.get("transform")
    if transform is None:
        return raw_value

    field_name = str(field_definition.get("name", "<unknown_field>"))
    try:
        result = eval(
            transform,
            {"__builtins__": {}},
            {"i": raw_value, "float": float},
        )
    except Exception as exc:
        raise ValueError(f"Ошибка transform для поля '{field_name}'") from exc

    return result
