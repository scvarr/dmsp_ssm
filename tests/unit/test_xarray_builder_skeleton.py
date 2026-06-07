import inspect

import numpy as np
import pytest
import xarray as xr

import dmsp_ssm._internal.builder.xarray_builder as xarray_builder_module
from dmsp_ssm._internal.builder import (
    XArrayBuilder,
    XArrayDimensionModel,
)
from dmsp_ssm._internal.format.definition import FormatDefinition
from dmsp_ssm._internal.pipeline import DecodedRecord

pytestmark = pytest.mark.unit


def _build_decoded_records_for_minimal_dataset() -> list[DecodedRecord]:
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


def test_xarray_builder_can_be_created() -> None:
    builder = XArrayBuilder()

    assert isinstance(builder, XArrayBuilder)


def test_xarray_builder_build_returns_dataset() -> None:
    builder = XArrayBuilder()
    decoded_records = _build_decoded_records_for_minimal_dataset()

    dataset = builder.build(decoded_records)

    assert isinstance(dataset, xr.Dataset)


def test_xarray_dimension_model_fixes_record_and_second_dimensions() -> None:
    schema = XArrayDimensionModel()

    assert schema.dimensions == ("record", "second")
    assert schema.dimensions != ("time",)


def test_xarray_dimension_model_fixes_coordinates() -> None:
    schema = XArrayDimensionModel()

    assert schema.coordinates == ("record_time", "second_index")
    assert schema.coordinate_dimensions("record_time") == ("record",)
    assert schema.coordinate_dimensions("second_index") == ("second",)


def test_xarray_dimension_model_fixes_data_variable_placement() -> None:
    schema = XArrayDimensionModel()

    assert schema.data_variables == ("bx", "by", "bz")
    assert schema.data_variable_dimensions("bx") == ("record", "second")
    assert schema.data_variable_dimensions("by") == ("record", "second")
    assert schema.data_variable_dimensions("bz") == ("record", "second")


def test_xarray_builder_dataset_has_required_dims_coords_and_data_vars() -> None:
    dataset = XArrayBuilder().build(_build_decoded_records_for_minimal_dataset())

    assert set(dataset.dims) == {"record", "second"}
    assert "record_time" in dataset.coords
    assert "second_index" in dataset.coords
    assert set(dataset.data_vars) == {
        "valid",
        "time",
        "bx",
        "by",
        "bz",
        "flight_number",
        "year",
        "day_of_year",
        "minute_start_sec_of_day",
        "latitude_deg",
        "longitude_deg",
        "altitude_km",
    }


def test_xarray_builder_dataset_shape_and_values_follow_decoded_second_data() -> None:
    dataset = XArrayBuilder().build(_build_decoded_records_for_minimal_dataset())

    assert dataset["valid"].shape == (2, 3)
    assert dataset["time"].shape == (2, 3)
    assert dataset["bx"].shape == (2, 3)
    assert dataset["by"].shape == (2, 3)
    assert dataset["bz"].shape == (2, 3)
    assert dataset["second_index"].values.tolist() == [0, 1, 2]

    assert dataset["valid"].dtype == bool
    assert dataset["valid"].values.tolist() == [[True, True, True], [True, True, True]]
    assert dataset["time"].values.tolist() == [[10.0, 11.0, 12.0], [20.0, 21.0, 22.0]]
    assert dataset["bx"].values.tolist() == [[1.0, 4.0, 7.0], [10.0, 13.0, 16.0]]
    assert dataset["by"].values.tolist() == [[2.0, 5.0, 8.0], [11.0, 14.0, 17.0]]
    assert dataset["bz"].values.tolist() == [[3.0, 6.0, 9.0], [12.0, 15.0, 18.0]]

    assert dataset["valid"].dims == ("record", "second")
    assert dataset["time"].dims == ("record", "second")


def test_xarray_builder_normalizes_missing_second_level_values_by_time_sentinel() -> None:
    dataset = XArrayBuilder().build(_build_decoded_records_with_missing_seconds())

    assert dataset["valid"].shape == (1, 3)
    assert dataset["time"].shape == (1, 3)
    assert dataset["bx"].shape == (1, 3)
    assert dataset["by"].shape == (1, 3)
    assert dataset["bz"].shape == (1, 3)

    assert dataset["time"].values[0, 0] == 10.0
    assert dataset["time"].values[0, 2] == 12.0
    assert dataset["bx"].values[0, 0] == 1.0
    assert dataset["bx"].values[0, 2] == 7.0

    assert dataset["valid"].dtype == bool
    assert dataset["valid"].values[0, 0]
    assert not dataset["valid"].values[0, 1]
    assert dataset["valid"].values[0, 2]

    assert float(dataset["time"].values[0, 1]) != -1000.0
    assert np.isnan(dataset["time"].values[0, 1])
    assert np.isnan(dataset["bx"].values[0, 1])
    assert np.isnan(dataset["by"].values[0, 1])
    assert np.isnan(dataset["bz"].values[0, 1])


def test_xarray_builder_dataset_contains_required_dataset_level_attrs() -> None:
    dataset = XArrayBuilder().build(_build_decoded_records_for_minimal_dataset())

    assert dataset.attrs["builder"] == "xarray"
    assert dataset.attrs["pipeline_terminal_stage"] == "builder"
    assert dataset.attrs["record_dimension"] == "record"
    assert dataset.attrs["second_dimension"] == "second"


def test_xarray_builder_adds_variable_units_from_format_definition() -> None:
    dataset = XArrayBuilder(
        format_definition=FormatDefinition().as_dict(),
    ).build(_build_decoded_records_for_minimal_dataset())

    assert dataset["year"].attrs["units"] == "year"
    assert dataset["day_of_year"].attrs["units"] == "day"
    assert dataset["minute_start_sec_of_day"].attrs["units"] == "s"
    assert dataset["latitude_deg"].attrs["units"] == "degree"
    assert dataset["longitude_deg"].attrs["units"] == "degree"
    assert dataset["altitude_km"].attrs["units"] == "km"
    assert dataset["time"].attrs["units"] == "s"
    assert dataset["bx"].attrs["units"] == "nT"
    assert dataset["by"].attrs["units"] == "nT"
    assert dataset["bz"].attrs["units"] == "nT"
    assert dataset["flight_number"].attrs["units"] == "1"
    assert "units" not in dataset["valid"].attrs


def test_xarray_builder_dataset_matches_frozen_contract_sets() -> None:
    dataset = XArrayBuilder().build(_build_decoded_records_for_minimal_dataset())

    expected_data_vars = set(XArrayBuilder.REQUIRED_SECOND_LEVEL_VARS) | set(
        XArrayBuilder.REQUIRED_RECORD_LEVEL_VARS
    )
    assert set(dataset.dims) == set(XArrayBuilder.REQUIRED_DIMS)
    assert set(dataset.coords) == set(XArrayBuilder.REQUIRED_COORDS)
    assert set(dataset.data_vars) == expected_data_vars
    assert set(dataset.attrs) == set(XArrayBuilder.REQUIRED_ATTRS)


def test_xarray_builder_dataset_attrs_do_not_duplicate_record_level_variables() -> None:
    dataset = XArrayBuilder().build(_build_decoded_records_for_minimal_dataset())

    assert "flight_number" not in dataset.attrs
    assert "year" not in dataset.attrs
    assert "day_of_year" not in dataset.attrs
    assert "minute_start_sec_of_day" not in dataset.attrs
    assert "latitude_deg" not in dataset.attrs
    assert "longitude_deg" not in dataset.attrs
    assert "altitude_km" not in dataset.attrs


def test_xarray_builder_dataset_contains_required_record_level_variables() -> None:
    dataset = XArrayBuilder().build(_build_decoded_records_for_minimal_dataset())

    assert dataset["flight_number"].dims == ("record",)
    assert dataset["year"].dims == ("record",)
    assert dataset["day_of_year"].dims == ("record",)
    assert dataset["minute_start_sec_of_day"].dims == ("record",)
    assert dataset["latitude_deg"].dims == ("record",)
    assert dataset["longitude_deg"].dims == ("record",)
    assert dataset["altitude_km"].dims == ("record",)

    assert dataset["flight_number"].values.tolist() == [101, 102]
    assert dataset["year"].values.tolist() == [2024, 2024]
    assert dataset["day_of_year"].values.tolist() == [100, 100]
    assert dataset["minute_start_sec_of_day"].values.tolist() == [60, 120]
    assert dataset["latitude_deg"].values.tolist() == [10.5, 11.5]
    assert dataset["longitude_deg"].values.tolist() == [20.5, 21.5]
    assert dataset["altitude_km"].values.tolist() == [850.0, 851.0]


def test_xarray_builder_module_does_not_depend_on_raw_layer() -> None:
    source_code = inspect.getsource(xarray_builder_module)

    assert "RawRecord" not in source_code
