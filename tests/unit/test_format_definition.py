import pytest

from dmsp_ssm._internal.format.definition_validator import FormatDefinitionValidator
from dmsp_ssm._internal.format.definition import FormatDefinition

pytestmark = pytest.mark.unit


def test_ssm_format_definition_rejects_empty_definition() -> None:
    validator = FormatDefinitionValidator()

    with pytest.raises(ValueError, match="record_size"):
        validator.validate({})


def test_ssm_format_definition_requires_byte_order(
    ssm_format_definition: dict,
) -> None:
    invalid_definition = dict(ssm_format_definition)
    invalid_definition.pop("byte_order")

    validator = FormatDefinitionValidator()

    with pytest.raises(ValueError, match="byte_order"):
        validator.validate(invalid_definition)


def test_ssm_format_definition_requires_validation_fields(
    ssm_format_definition: dict,
) -> None:
    invalid_definition = dict(ssm_format_definition)
    invalid_definition.pop("validation_fields")

    validator = FormatDefinitionValidator()

    with pytest.raises(ValueError, match="validation_fields"):
        validator.validate(invalid_definition)


def test_ssm_format_definition_rejects_unknown_validation_field(
    ssm_format_definition: dict,
) -> None:
    invalid_definition = {
        **ssm_format_definition,
        "validation_fields": ["year", "unknown_field"],
    }

    validator = FormatDefinitionValidator()

    with pytest.raises(ValueError, match="unknown_field"):
        validator.validate(invalid_definition)


def test_ssm_format_definition_class_contains_required_keys() -> None:
    format_definition = FormatDefinition().as_dict()

    assert "record_size" in format_definition
    assert "byte_order" in format_definition
    assert "validation_fields" in format_definition
    assert format_definition["validation_fields"] == ["year", "day_of_year"]


def test_ssm_format_definition_as_dict_returns_independent_copy() -> None:
    format_definition = FormatDefinition()

    first = format_definition.as_dict()
    second = format_definition.as_dict()

    first["record_size"] = -1

    assert second["record_size"] == 988


def test_ssm_format_definition_contains_units_for_output_fields() -> None:
    format_definition = FormatDefinition().as_dict()
    second_data = next(
        block for block in format_definition["blocks"] if block["name"] == "second_data"
    )
    fields_by_name = {
        field["name"]: field
        for field in (
            format_definition["header"]
            + second_data["fields"]
            + format_definition["footer"]
        )
    }

    assert fields_by_name["year"]["unit"] == "year"
    assert fields_by_name["day_of_year"]["unit"] == "day"
    assert fields_by_name["first_minute_first_second_time"]["unit"] == "s"
    assert fields_by_name["geodetic_latitude"]["unit"] == "degree"
    assert fields_by_name["geographic_longitude"]["unit"] == "degree"
    assert fields_by_name["altitude_km"]["unit"] == "km"
    assert fields_by_name["time"]["unit"] == "s"
    assert fields_by_name["bx"]["unit"] == "nT"
    assert fields_by_name["by"]["unit"] == "nT"
    assert fields_by_name["bz"]["unit"] == "nT"
    assert fields_by_name["flight_number"]["unit"] == "1"
