import pytest

from dmsp_ssm import ParseOptions, ParseResult, Reader, __version__
import dmsp_ssm

pytestmark = pytest.mark.unit


def test_package_exposes_version() -> None:
    assert __version__ == "1.0.0"


def test_package_exposes_parse_options() -> None:
    options = ParseOptions()

    assert options.recursive is True
    assert options.error_policy is None


def test_package_freezes_v1_public_api_surface() -> None:
    assert dmsp_ssm.__all__ == ["Reader", "ParseOptions", "ParseResult"]
    assert Reader is dmsp_ssm.Reader
    assert ParseOptions is dmsp_ssm.ParseOptions
    assert ParseResult is dmsp_ssm.ParseResult
