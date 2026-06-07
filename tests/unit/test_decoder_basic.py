from __future__ import annotations

import pytest

from dmsp_ssm._internal.decoder import Decoder
from dmsp_ssm._internal.format.definition import FormatDefinition
from dmsp_ssm._internal.pipeline import RawRecord

pytestmark = pytest.mark.unit


def _build_raw_record() -> RawRecord:
    return RawRecord(
        raw_bytes=b"raw-record",
        header={
            "year": 2024,
            "day_of_year": 123,
            "first_minute_first_second_time": 12345,
            "geodetic_latitude": 9012,
            "geographic_longitude": 12345,
            "altitude_km": 543,
        },
        blocks={
            "second_data": [
                {
                    "time": 1000 + index,
                    "bx": 10 + index,
                    "by": 20 + index,
                    "bz": 30 + index,
                }
                for index in range(60)
            ]
        },
        footer={"flight_number": 11},
    )


def test_decoder_applies_header_transforms() -> None:
    decoder = Decoder(format_definition=FormatDefinition().as_dict())
    decoded = decoder.decode(_build_raw_record())

    assert decoded.header["first_minute_first_second_time"] == pytest.approx(12.345)
    assert decoded.header["geodetic_latitude"] == pytest.approx(0.12)
    assert decoded.header["geographic_longitude"] == pytest.approx(123.45)
    assert decoded.header["altitude_km"] == pytest.approx(54.3)


def test_decoder_keeps_header_and_footer_fields_without_transform() -> None:
    decoder = Decoder(format_definition=FormatDefinition().as_dict())
    decoded = decoder.decode(_build_raw_record())

    assert decoded.header["year"] == 2024
    assert decoded.header["day_of_year"] == 123
    assert decoded.footer["flight_number"] == 11


def test_decoder_decodes_block_fields_with_repeat() -> None:
    decoder = Decoder(format_definition=FormatDefinition().as_dict())
    decoded = decoder.decode(_build_raw_record())

    assert len(decoded.blocks["second_data"]) == 60
    assert decoded.blocks["second_data"][0]["time"] == pytest.approx(1.0)
    assert decoded.blocks["second_data"][59]["time"] == pytest.approx(1.059)
    assert decoded.blocks["second_data"][0]["bx"] == 10
    assert decoded.blocks["second_data"][0]["by"] == 20
    assert decoded.blocks["second_data"][0]["bz"] == 30


def test_decoder_preserves_raw_to_decoded_structure_without_raw_bytes_field() -> None:
    raw_record = _build_raw_record()
    decoder = Decoder(format_definition=FormatDefinition().as_dict())
    decoded = decoder.decode(raw_record)

    assert set(decoded.header) == set(raw_record.header)
    assert set(decoded.blocks) == set(raw_record.blocks)
    assert len(decoded.blocks["second_data"]) == len(raw_record.blocks["second_data"])
    assert set(decoded.blocks["second_data"][0]) == set(raw_record.blocks["second_data"][0])
    assert set(decoded.footer) == set(raw_record.footer)
    assert not hasattr(decoded, "raw_bytes")
