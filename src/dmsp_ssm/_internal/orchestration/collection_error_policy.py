"""Внутренняя политика ошибок коллекции для обработки файлов читателем."""

from __future__ import annotations


class CollectionErrorPolicy:
    """Внутренние policy для обработки ошибки одного файла в коллекции."""

    FAIL_FAST = "fail_fast"
    SKIP_FAILED_FILE = "skip_failed_file"
    ALL = {FAIL_FAST, SKIP_FAILED_FILE}
