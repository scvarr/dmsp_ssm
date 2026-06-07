import inspect

import pytest

import dmsp_ssm._internal.assembler.contracts as assembler_contracts
from dmsp_ssm._internal.assembler import (
    ProfileArtifactRequirements,
    OUTPUT_PROFILE_ARTIFACT_REQUIREMENTS,
)

pytestmark = pytest.mark.unit


def test_profile_requirements_map_exists_and_has_required_profiles() -> None:
    assert set(OUTPUT_PROFILE_ARTIFACT_REQUIREMENTS) == {
        "raw",
        "decoded",
        "xarray",
        "numpy",
        "table",
    }


def test_profile_requirements_map_has_expected_required_artifacts() -> None:
    assert (
            OUTPUT_PROFILE_ARTIFACT_REQUIREMENTS["raw"].required_artifacts
            == frozenset({"raw_records"})
    )
    assert (
            OUTPUT_PROFILE_ARTIFACT_REQUIREMENTS["decoded"].required_artifacts
            == frozenset({"decoded_records"})
    )
    assert (
            OUTPUT_PROFILE_ARTIFACT_REQUIREMENTS["xarray"].required_artifacts
            == frozenset({"dataset"})
    )
    assert (
            OUTPUT_PROFILE_ARTIFACT_REQUIREMENTS["numpy"].required_artifacts
            == frozenset({"numpy_records"})
    )
    assert (
            OUTPUT_PROFILE_ARTIFACT_REQUIREMENTS["table"].required_artifacts
            == frozenset({"table_records"})
    )


def test_profile_requirements_map_uses_contract_objects_without_runtime_execution_logic() -> None:
    assert all(
        isinstance(requirements, ProfileArtifactRequirements)
        for requirements in OUTPUT_PROFILE_ARTIFACT_REQUIREMENTS.values()
    )

    source_code = inspect.getsource(assembler_contracts)
    assert "parse(" not in source_code
    assert "decode(" not in source_code
    assert ".build(" not in source_code
