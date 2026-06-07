from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

from dmsp_ssm.reader import Reader
from dmsp_ssm._internal.pipeline.raw_record import RawRecord
from dmsp_ssm._internal.pipeline.field_trace import FieldTrace
from dmsp_ssm._internal.pipeline.decoded_record import DecodedRecord
from dmsp_ssm._internal.validator.contracts import ValidationResult
from dmsp_ssm._internal.assembler.artifact_accumulator import accumulate_artifact_bundle
from dmsp_ssm._internal.builder.table_builder import TableBuilder

pytestmark = pytest.mark.unit


def _build_raw_records() -> list[RawRecord]:
    return [
        RawRecord(
            raw_bytes=b"r1",
            header={
                "year": 2024,
                "day_of_year": 100,
                "first_minute_first_second_time": 60,
                "geodetic_latitude": 10,
                "geographic_longitude": 20,
                "altitude_km": 30,
            },
            blocks={
                "second_data": [
                    {"time": 1, "bx": 1, "by": 2, "bz": 3},
                    {"time": 2, "bx": 4, "by": 5, "bz": 6},
                ]
            },
            footer={"flight_number": 1},
        ),
        RawRecord(
            raw_bytes=b"r2",
            header={
                "year": 2024,
                "day_of_year": 100,
                "first_minute_first_second_time": 120,
                "geodetic_latitude": 11,
                "geographic_longitude": 21,
                "altitude_km": 31,
            },
            blocks={
                "second_data": [
                    {"time": 3, "bx": 7, "by": 8, "bz": 9},
                    {"time": 4, "bx": 10, "by": 11, "bz": 12},
                ]
            },
            footer={"flight_number": 2},
        ),
    ]


def _build_field_traces() -> list[FieldTrace]:
    return [
        FieldTrace(
            record_index=0,
            second_index=None,
            section="header",
            field_name="year",
            field_role="record",
            byte_offset=0,
            byte_length=4,
            raw_hex="000007E8",
            raw_int=2024,
            unit=None,
            transform=None,
        )
    ]


def _build_table_field_traces() -> list[FieldTrace]:
    return [
        FieldTrace(
            record_index=0,
            second_index=0,
            section="second_data",
            field_name="time",
            field_role="second",
            byte_offset=24,
            byte_length=4,
            raw_hex="FFFFFC18",
            raw_int=-1000,
            unit=None,
            transform=None,
        ),
        FieldTrace(
            record_index=0,
            second_index=0,
            section="second_data",
            field_name="bx",
            field_role="second",
            byte_offset=28,
            byte_length=4,
            raw_hex="00000001",
            raw_int=1,
            unit=None,
            transform=None,
        ),
    ]


class _DecoderStub:
    def __init__(self) -> None:
        self.calls: list[bytes] = []

    def decode(self, record: RawRecord) -> DecodedRecord:
        self.calls.append(record.raw_bytes)
        return DecodedRecord(
            header=dict(record.header),
            blocks=dict(record.blocks),
            footer=dict(record.footer),
        )


class _BuilderStub:
    def __init__(self) -> None:
        self.calls: list[list[object]] = []

    def build(self, records: list[object]) -> xr.Dataset:
        self.calls.append(records)
        return xr.Dataset(
            data_vars={"bx": (("record", "second"), [[1.0], [2.0]])},
            coords={
                "record_time": ("record", [0, 1]),
                "second_index": ("second", [0]),
            },
        )


class _NumpyBuilderStub:
    def __init__(self) -> None:
        self.calls: list[list[object]] = []

    def build(self, records: list[object]) -> dict[str, np.ndarray]:
        self.calls.append(records)
        return {
            "time": np.array([[1.0], [2.0]]),
            "bx": np.array([[1.0], [2.0]]),
            "by": np.array([[1.0], [2.0]]),
            "bz": np.array([[1.0], [2.0]]),
            "valid": np.array([[True], [True]]),
            "flight_number": np.array([1, 2]),
            "year": np.array([2024, 2024]),
            "day_of_year": np.array([100, 100]),
            "minute_start_sec_of_day": np.array([60, 120]),
            "latitude_deg": np.array([10.0, 11.0]),
            "longitude_deg": np.array([20.0, 21.0]),
            "altitude_km": np.array([30.0, 31.0]),
        }


def test_reader_accumulation_raw_profile_prepares_only_raw_records() -> None:
    decoder = _DecoderStub()
    builder = _BuilderStub()
    numpy_builder = _NumpyBuilderStub()

    report = ValidationResult(status="ok", validated_chunks=[])
    bundle = accumulate_artifact_bundle(
        profile="raw",
        raw_records=_build_raw_records(),
        field_traces=_build_field_traces(),
        report=report,
        decoder=decoder,
        builder=builder,
        numpy_builder=numpy_builder,
    )

    assert bundle.report is report
    assert bundle.raw_records is not None
    assert bundle.field_traces is not None
    assert bundle.decoded_records is None
    assert bundle.dataset is None
    assert bundle.numpy_records is None
    assert decoder.calls == []
    assert builder.calls == []
    assert numpy_builder.calls == []


def test_reader_accumulation_decoded_profile_prepares_decoded_without_dataset() -> None:
    decoder = _DecoderStub()
    builder = _BuilderStub()
    numpy_builder = _NumpyBuilderStub()

    report = ValidationResult(status="ok", validated_chunks=[])
    bundle = accumulate_artifact_bundle(
        profile="decoded",
        raw_records=_build_raw_records(),
        field_traces=_build_field_traces(),
        report=report,
        decoder=decoder,
        builder=builder,
        numpy_builder=numpy_builder,
    )

    assert bundle.report is report
    assert bundle.raw_records is None
    assert bundle.field_traces is not None
    assert bundle.decoded_records is not None
    assert len(bundle.decoded_records) == 2
    assert bundle.dataset is None
    assert bundle.numpy_records is None
    assert decoder.calls == [b"r1", b"r2"]
    assert builder.calls == []
    assert numpy_builder.calls == []


def test_reader_accumulation_xarray_profile_prepares_dataset() -> None:
    decoder = _DecoderStub()
    builder = _BuilderStub()
    numpy_builder = _NumpyBuilderStub()

    report = ValidationResult(status="ok", validated_chunks=[])
    bundle = accumulate_artifact_bundle(
        profile="xarray",
        raw_records=_build_raw_records(),
        field_traces=_build_field_traces(),
        report=report,
        decoder=decoder,
        builder=builder,
        numpy_builder=numpy_builder,
    )

    assert bundle.report is report
    assert bundle.raw_records is None
    assert bundle.field_traces is not None
    assert bundle.decoded_records is None
    assert isinstance(bundle.dataset, xr.Dataset)
    assert bundle.numpy_records is None
    assert decoder.calls == [b"r1", b"r2"]
    assert len(builder.calls) == 1
    assert len(builder.calls[0]) == 2
    assert numpy_builder.calls == []


def test_reader_accumulation_numpy_profile_prepares_numpy_records() -> None:
    decoder = _DecoderStub()
    builder = _BuilderStub()
    numpy_builder = _NumpyBuilderStub()

    report = ValidationResult(status="ok", validated_chunks=[])
    bundle = accumulate_artifact_bundle(
        profile="numpy",
        raw_records=_build_raw_records(),
        field_traces=_build_field_traces(),
        report=report,
        decoder=decoder,
        builder=builder,
        numpy_builder=numpy_builder,
    )

    assert bundle.report is report
    assert bundle.raw_records is None
    assert bundle.field_traces is not None
    assert bundle.decoded_records is None
    assert bundle.dataset is None
    assert isinstance(bundle.numpy_records, dict)
    assert set(bundle.numpy_records) == {
        "time",
        "bx",
        "by",
        "bz",
        "valid",
        "flight_number",
        "year",
        "day_of_year",
        "minute_start_sec_of_day",
        "latitude_deg",
        "longitude_deg",
        "altitude_km",
    }
    assert decoder.calls == [b"r1", b"r2"]
    assert builder.calls == []
    assert len(numpy_builder.calls) == 1


def test_reader_accumulation_table_profile_builds_table_records_via_table_builder() -> None:
    decoder = _DecoderStub()
    builder = _BuilderStub()
    numpy_builder = _NumpyBuilderStub()
    table_builder = TableBuilder()

    report = ValidationResult(status="ok", validated_chunks=[])
    bundle = accumulate_artifact_bundle(
        profile="table",
        raw_records=_build_raw_records(),
        field_traces=_build_table_field_traces(),
        report=report,
        decoder=decoder,
        builder=builder,
        numpy_builder=numpy_builder,
        table_builder=table_builder,
    )

    assert bundle.report is report
    assert bundle.field_traces is not None
    assert bundle.raw_records is None
    assert bundle.decoded_records is not None
    assert bundle.dataset is None
    assert bundle.numpy_records is None
    assert bundle.table_records is not None
    assert bundle.table_records[0]["field_name"] == "time"
    assert bundle.table_records[0]["decoded_value"] == 1
    assert bundle.table_records[0]["normalized_value"] == 1
    assert bundle.table_records[0]["valid"] is True
    assert bundle.table_records[1]["field_name"] == "bx"
    assert bundle.table_records[1]["decoded_value"] == 1
    assert bundle.table_records[1]["normalized_value"] == 1
    assert bundle.table_records[1]["valid"] is True
    assert decoder.calls == [b"r1", b"r2"]
    assert builder.calls == []
    assert numpy_builder.calls == []


def test_reader_accumulation_table_profile_missing_second_normalization_applied() -> None:
    decoder = _DecoderStub()
    builder = _BuilderStub()
    numpy_builder = _NumpyBuilderStub()
    table_builder = TableBuilder()
    report = ValidationResult(status="ok", validated_chunks=[])

    raw_records = _build_raw_records()
    raw_records[0].blocks["second_data"][0]["time"] = -1000
    raw_records[0].blocks["second_data"][0]["bx"] = 7

    traces = [
        FieldTrace(
            record_index=0,
            second_index=0,
            section="second_data",
            field_name="time",
            field_role="second",
            byte_offset=24,
            byte_length=4,
            raw_hex="FFFFFC18",
            raw_int=-1000,
            unit=None,
            transform=None,
        ),
        FieldTrace(
            record_index=0,
            second_index=0,
            section="second_data",
            field_name="bx",
            field_role="second",
            byte_offset=28,
            byte_length=4,
            raw_hex="00000007",
            raw_int=7,
            unit=None,
            transform=None,
        ),
    ]
    bundle = accumulate_artifact_bundle(
        profile="table",
        raw_records=raw_records,
        field_traces=traces,
        report=report,
        decoder=decoder,
        builder=builder,
        numpy_builder=numpy_builder,
        table_builder=table_builder,
    )

    assert bundle.table_records is not None
    time_row, bx_row = bundle.table_records
    assert time_row["decoded_value"] == -1000.0
    assert time_row["normalized_value"] is None
    assert time_row["valid"] is False
    assert bx_row["decoded_value"] == 7
    assert bx_row["normalized_value"] is None
    assert bx_row["valid"] is False


def test_reader_accumulation_table_profile_requires_table_builder() -> None:
    decoder = _DecoderStub()
    builder = _BuilderStub()
    numpy_builder = _NumpyBuilderStub()
    report = ValidationResult(status="ok", validated_chunks=[])

    with pytest.raises(
        ValueError,
        match=r"^Для internal profile 'table' требуется table_builder\.$",
    ):
        accumulate_artifact_bundle(
            profile="table",
            raw_records=_build_raw_records(),
            field_traces=_build_table_field_traces(),
            report=report,
            decoder=decoder,
            builder=builder,
            numpy_builder=numpy_builder,
            table_builder=None,
        )


def test_reader_accumulation_carries_field_traces_without_affecting_numpy_result() -> None:
    decoder = _DecoderStub()
    builder = _BuilderStub()
    numpy_builder = _NumpyBuilderStub()
    traces = _build_field_traces()
    report = ValidationResult(status="ok", validated_chunks=[])

    bundle = accumulate_artifact_bundle(
        profile="numpy",
        raw_records=_build_raw_records(),
        field_traces=traces,
        report=report,
        decoder=decoder,
        builder=builder,
        numpy_builder=numpy_builder,
    )

    assert bundle.field_traces is traces
    assert isinstance(bundle.numpy_records, dict)
