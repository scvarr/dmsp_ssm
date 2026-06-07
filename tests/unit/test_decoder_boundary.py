from __future__ import annotations

import pytest

from dmsp_ssm._internal.pipeline.decoded_record import DecodedRecord
from dmsp_ssm._internal.decoder.decoder import Decoder
from dmsp_ssm._internal.format.definition import FormatDefinition
from dmsp_ssm._internal.pipeline.raw_record import RawRecord

pytestmark = pytest.mark.unit


def _build_raw_record() -> RawRecord:
    return RawRecord(
        raw_bytes=b"boundary-raw-record",
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


def test_decoder_boundary_accepts_raw_record_and_returns_decoded_record() -> None:
    decoder = Decoder(format_definition=FormatDefinition().as_dict())

    decoded = decoder.decode(_build_raw_record())

    assert isinstance(decoded, DecodedRecord)


def test_decoder_boundary_preserves_sections_shape() -> None:
    raw_record = _build_raw_record()
    decoder = Decoder(format_definition=FormatDefinition().as_dict())

    decoded = decoder.decode(raw_record)

    assert set(decoded.header) == set(raw_record.header)
    assert set(decoded.blocks) == set(raw_record.blocks)
    assert len(decoded.blocks["second_data"]) == len(raw_record.blocks["second_data"])
    assert set(decoded.blocks["second_data"][0]) == set(raw_record.blocks["second_data"][0])
    assert set(decoded.footer) == set(raw_record.footer)


def test_decoder_boundary_applies_transform_and_keeps_passthrough() -> None:
    decoder = Decoder(format_definition=FormatDefinition().as_dict())

    decoded = decoder.decode(_build_raw_record())

    assert decoded.header["first_minute_first_second_time"] == pytest.approx(12.345)
    assert decoded.blocks["second_data"][0]["time"] == pytest.approx(1.0)
    assert decoded.header["year"] == 2024
    assert decoded.blocks["second_data"][0]["bx"] == 10
