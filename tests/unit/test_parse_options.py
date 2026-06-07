import pytest

from dmsp_ssm.parse_options import ParseOptions
from dmsp_ssm._internal.validator.policy import ValidationErrorPolicy

pytestmark = pytest.mark.unit


def test_parse_options_defaults_match_canonical_parse_call() -> None:
    options = ParseOptions()

    assert options.recursive is True
    assert options.error_policy is None
    assert options.output_profile == "xarray"


def test_parse_options_public_output_profiles_set_matches_public_contract() -> None:
    assert ParseOptions.PUBLIC_OUTPUT_PROFILES == frozenset({"xarray", "numpy", "table"})
    assert "raw" not in ParseOptions.PUBLIC_OUTPUT_PROFILES
    assert "decoded" not in ParseOptions.PUBLIC_OUTPUT_PROFILES


def test_parse_options_accepts_explicit_values() -> None:
    options = ParseOptions(
        recursive=True,
        error_policy=ValidationErrorPolicy.RESYNC,
        output_profile="xarray",
    )

    assert options.recursive is True
    assert options.error_policy == ValidationErrorPolicy.RESYNC
    assert options.output_profile == "xarray"


@pytest.mark.parametrize("output_profile", ["xarray", "numpy", "table"])
def test_parse_options_accepts_public_output_profiles(output_profile: str) -> None:
    options = ParseOptions(output_profile=output_profile)

    assert options.output_profile == output_profile


@pytest.mark.parametrize("output_profile", ["raw", "decoded", "unknown"])
def test_parse_options_rejects_non_public_output_profiles(
    output_profile: str,
) -> None:
    with pytest.raises(ValueError, match="output_profile"):
        ParseOptions(output_profile=output_profile)
