"""Внутренний модуль доступа к файлам источника данных."""

from __future__ import annotations

import gzip
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class SourceFile:
    """Внутренний дескриптор одного поддерживаемого файла источника."""

    path: Path
    kind: Literal["dat", "gz"]


class DataSource:
    """Адаптер источника данных для поиска файлов и чтения байтов."""

    def __init__(self, path: str | Path, *, recursive: bool = False):
        self.path = Path(path)
        self.recursive = recursive

    def list_source_files(self) -> list[SourceFile]:
        """Вернуть поддерживаемые файлы .dat/.gz в детерминированном порядке."""

        if self.path.is_dir():
            return self._discover_directory_source_files()

        return [self._discover_single_source_file()]

    def read_source_file(self, source_file: SourceFile) -> bytes:
        """Прочитать байты одного дескриптора файла источника."""

        if source_file.kind == "dat":
            return self._read_dat_file(source_file.path)
        if source_file.kind == "gz":
            return self._read_gz_file(source_file.path)
        raise ValueError("Неподдерживаемый тип source file")

    def _discover_single_source_file(self) -> SourceFile:
        """Определить поддерживаемый одиночный файл источника по расширению."""

        if self.path.suffix == ".dat":
            return SourceFile(path=self.path, kind="dat")
        if self.path.suffix == ".gz":
            return SourceFile(path=self.path, kind="gz")
        raise ValueError("Поддерживаются только файлы .dat или .gz")

    def _discover_directory_source_files(self) -> list[SourceFile]:
        """Найти файлы источника в каталоге и применить правила валидности набора."""

        entries = list(self.path.iterdir())
        all_files = self._collect_files()

        if not entries:
            raise ValueError("Каталог пустой")

        # В recursive-режиме каталог может содержать только вложенные директории.
        # Это по-прежнему считается пустым источником данных.
        if self.recursive and not all_files:
            raise ValueError("Каталог пустой")

        dat_files, gz_files, unsupported_files = self._split_files_by_type(all_files)
        self._validate_directory_file_mix(
            dat_files=dat_files,
            gz_files=gz_files,
            unsupported_files=unsupported_files,
        )
        return self._build_source_file_descriptors(dat_files=dat_files, gz_files=gz_files)

    @staticmethod
    def _split_files_by_type(
        all_files: list[Path],
    ) -> tuple[list[Path], list[Path], list[Path]]:
        """Разделить список файлов каталога по типам расширений."""

        dat_files = [path for path in all_files if path.suffix == ".dat"]
        gz_files = [path for path in all_files if path.suffix == ".gz"]
        unsupported_files = [
            path for path in all_files if path.suffix not in (".dat", ".gz")
        ]
        return dat_files, gz_files, unsupported_files

    @staticmethod
    def _validate_directory_file_mix(
        *,
        dat_files: list[Path],
        gz_files: list[Path],
        unsupported_files: list[Path],
    ) -> None:
        """Проверить допустимость набора файлов каталога по контракту источника."""

        if unsupported_files:
            raise ValueError("Каталог содержит неподдерживаемые файлы")
        if dat_files and gz_files:
            raise ValueError("Каталог содержит смешанные типы файлов")

    @staticmethod
    def _build_source_file_descriptors(
        *,
        dat_files: list[Path],
        gz_files: list[Path],
    ) -> list[SourceFile]:
        """Собрать дескрипторы файлов источника в согласованном формате."""

        if dat_files:
            return [SourceFile(path=file_path, kind="dat") for file_path in dat_files]
        return [SourceFile(path=file_path, kind="gz") for file_path in gz_files]

    def _collect_files(self) -> list[Path]:
        """Собрать файлы в детерминированном порядке."""

        if self.recursive:
            files = [p for p in self.path.rglob("*") if p.is_file()]
            # Сортировать по относительному пути для стабильного порядка между платформами.
            return sorted(files, key=lambda p: p.relative_to(self.path).parts)

        files = [p for p in self.path.iterdir() if p.is_file()]
        return sorted(files)

    @staticmethod
    def _read_gz_file(path: Path) -> bytes:
        """Прочитать gzip-файл и вернуть распакованные байты."""

        with gzip.open(path, "rb") as stream:
            return stream.read()

    @staticmethod
    def _read_dat_file(path: Path) -> bytes:
        """Прочитать dat-файл и вернуть байты без дополнительной обработки."""

        with path.open("rb") as stream:
            return stream.read()
