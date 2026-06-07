import inspect

import numpy as np
import pytest

import dmsp_ssm._internal.builder.numpy_builder as numpy_builder_module
from dmsp_ssm._internal.builder import NumpyBuilder
from dmsp_ssm._internal.pipeline import DecodedRecord

pytestmark = pytest.mark.unit


def _build_decoded_records_for_numpy() -> list[DecodedRecord]:
    return [
        DecodedRecord(
            header={
                "year": 2024,
                "day_of_year": 100,
                "first_minute_first_second_time": 60,
                "geodetic_latitude": 10.5,
                "geographic_longitude": 20.5,
                "altitude_km": 850.0,
            },
            blocks={
                "second_data": [
                    {"time": 10.0, "bx": 1.0, "by": 2.0, "bz": 3.0},
                    {"time": 11.0, "bx": 4.0, "by": 5.0, "bz": 6.0},
                    {"time": 12.0, "bx": 7.0, "by": 8.0, "bz": 9.0},
                ]
            },
            footer={"flight_number": 101},
        ),
        DecodedRecord(
            header={
                "year": 2024,
                "day_of_year": 100,
                "first_minute_first_second_time": 120,
                "geodetic_latitude": 11.5,
                "geographic_longitude": 21.5,
                "altitude_km": 851.0,
            },
            blocks={
                "second_data": [
                    {"time": 20.0, "bx": 10.0, "by": 11.0, "bz": 12.0},
                    {"time": 21.0, "bx": 13.0, "by": 14.0, "bz": 15.0},
                    {"time": 22.0, "bx": 16.0, "by": 17.0, "bz": 18.0},
                ]
            },
            footer={"flight_number": 102},
        ),
    ]


def _build_decoded_records_with_missing_seconds() -> list[DecodedRecord]:
    return [
        DecodedRecord(
            header={
                "year": 2024,
                "day_of_year": 100,
                "first_minute_first_second_time": 60,
                "geodetic_latitude": 10.5,
                "geographic_longitude": 20.5,
                "altitude_km": 850.0,
            },
            blocks={
                "second_data": [
                    {"time": 10.0, "bx": 1.0, "by": 2.0, "bz": 3.0},
                    {"time": -1000.0, "bx": 0.0, "by": 0.0, "bz": 0.0},
                    {"time": 12.0, "bx": 7.0, "by": 8.0, "bz": 9.0},
                ]
            },
            footer={"flight_number": 101},
        )
    ]


def test_numpy_builder_build_returns_dict_with_required_keys() -> None:
    records = NumpyBuilder().build(_build_decoded_records_for_numpy())

    assert isinstance(records, dict)
    assert set(records) == {
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
    assert all(isinstance(value, np.ndarray) for value in records.values())


def test_numpy_builder_does_not_add_units_metadata_to_records() -> None:
    records = NumpyBuilder().build(_build_decoded_records_for_numpy())

    assert "units" not in records
    assert "metadata" not in records


def test_numpy_builder_shapes_follow_record_and_second_counts() -> None:
    records = NumpyBuilder().build(_build_decoded_records_for_numpy())

    assert records["time"].shape == (2, 3)
    assert records["bx"].shape == (2, 3)
    assert records["by"].shape == (2, 3)
    assert records["bz"].shape == (2, 3)
    assert records["valid"].shape == (2, 3)
    assert records["flight_number"].shape == (2,)
    assert records["year"].shape == (2,)
    assert records["day_of_year"].shape == (2,)
    assert records["minute_start_sec_of_day"].shape == (2,)
    assert records["latitude_deg"].shape == (2,)
    assert records["longitude_deg"].shape == (2,)
    assert records["altitude_km"].shape == (2,)


def test_numpy_builder_normalizes_missing_by_time_sentinel() -> None:
    records = NumpyBuilder().build(_build_decoded_records_with_missing_seconds())

    assert records["valid"].dtype == bool
    assert records["valid"].shape == (1, 3)
    assert records["valid"][0, 0]
    assert not records["valid"][0, 1]
    assert records["valid"][0, 2]

    assert np.isnan(records["time"][0, 1])
    assert np.isnan(records["bx"][0, 1])
    assert np.isnan(records["by"][0, 1])
    assert np.isnan(records["bz"][0, 1])


def test_numpy_builder_module_does_not_depend_on_xarray() -> None:
    source_code = inspect.getsource(numpy_builder_module)

    assert "xarray" not in source_code
