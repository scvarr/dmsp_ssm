"""Политики обработки ошибок валидации."""

class ValidationErrorPolicy:
    """Допустимые политики обработки ошибок."""

    STRICT = "strict"
    RESYNC = "resync"

    ALL = {STRICT, RESYNC}