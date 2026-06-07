import pytest

from dmsp_ssm._internal.validator.field_resolver import ValidationFieldResolver

pytestmark = pytest.mark.unit


def test_validation_field_resolver_returns_only_validation_fields(
    ssm_format_definition: dict,
) -> None:
    resolver = ValidationFieldResolver(format_definition=ssm_format_definition)

    resolved = resolver.resolve()

    assert set(resolved) == set(ssm_format_definition["validation_fields"])
    assert "geodetic_latitude" not in resolved


def test_validation_field_resolver_resolves_only_required_validation_fields(
    ssm_format_definition: dict,
) -> None:
    resolver = ValidationFieldResolver(format_definition=ssm_format_definition)

    resolved = resolver.resolve()

    assert resolved["year"]["offset"] == 0
    assert resolved["day_of_year"]["offset"] == 4
    assert resolver.field_definitions["flight_number"]["offset"] == 984
    assert "flight_number" not in resolved
