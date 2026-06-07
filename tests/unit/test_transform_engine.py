import pytest

from dmsp_ssm._internal.decoder.transform import apply_transform

pytestmark = pytest.mark.unit


def test_apply_transform_returns_raw_value_when_transform_missing() -> None:
    field_definition = {"name": "year"}

    assert apply_transform(raw_value=2024, field_definition=field_definition) == 2024


def test_apply_transform_applies_simple_formula() -> None:
    field_definition = {
        "name": "geodetic_latitude",
        "transform": "float(i)/1000.0",
    }

    assert apply_transform(raw_value=12345, field_definition=field_definition) == 12.345


def test_apply_transform_raises_value_error_when_formula_invalid() -> None:
    field_definition = {
        "name": "geodetic_latitude",
        "transform": "float(i) / unknown_name",
    }

    with pytest.raises(ValueError, match="geodetic_latitude"):
        apply_transform(raw_value=9123, field_definition=field_definition)
