import pytest

from dmsp_ssm._internal.format.layout import build_field_definitions

pytestmark = pytest.mark.unit


def test_build_field_definitions_merges_header_and_footer_by_name(
    ssm_format_definition: dict,
) -> None:
    field_definitions = build_field_definitions(ssm_format_definition)

    expected_field_count = (
        len(ssm_format_definition["header"]) + len(ssm_format_definition["footer"])
    )
    assert len(field_definitions) == expected_field_count
    assert {"year", "day_of_year", "flight_number"}.issubset(set(field_definitions))
    assert field_definitions["year"]["offset"] == 0
    assert field_definitions["day_of_year"]["offset"] == 4
    assert field_definitions["flight_number"]["offset"] == 984
