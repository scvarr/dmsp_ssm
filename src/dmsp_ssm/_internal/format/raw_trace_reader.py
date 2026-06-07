"""Низкоуровневое чтение raw-значений для trace-представления."""

from __future__ import annotations


def read_raw_hex(
    chunk: bytes,
    byte_offset: int,
    byte_length: int,
) -> str:
    """Прочитать байтовый срез как uppercase hex без префикса `0x`."""

    start, end = _validate_slice_bounds(
        chunk=chunk,
        byte_offset=byte_offset,
        byte_length=byte_length,
    )
    return chunk[start:end].hex().upper()


def read_raw_int(
    chunk: bytes,
    byte_offset: int,
    byte_length: int,
    byte_order: str,
) -> int:
    """Прочитать байтовый срез как signed raw integer."""

    if byte_order not in {"little", "big"}:
        raise ValueError(
            f"Неподдерживаемый byte_order: {byte_order!r}. Поддерживаются: 'little', 'big'."
        )
    start, end = _validate_slice_bounds(
        chunk=chunk,
        byte_offset=byte_offset,
        byte_length=byte_length,
    )
    return int.from_bytes(
        chunk[start:end],
        byteorder=byte_order,
        signed=True,
    )


def _validate_slice_bounds(
    *,
    chunk: bytes,
    byte_offset: int,
    byte_length: int,
) -> tuple[int, int]:
    """Проверить границы байтового среза внутри chunk."""

    if byte_offset < 0:
        raise ValueError("Параметр byte_offset не может быть отрицательным.")
    if byte_length <= 0:
        raise ValueError("Параметр byte_length должен быть положительным.")

    end = byte_offset + byte_length
    if end > len(chunk):
        raise ValueError("Срез выходит за границы chunk.")
    return byte_offset, end
