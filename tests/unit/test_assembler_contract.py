import inspect
from typing import get_type_hints

import numpy as np
import pytest
import xarray as xr

import dmsp_ssm._internal.assembler.contracts as assembler_contracts
from dmsp_ssm._internal.assembler.contracts import (
    ArtifactBundle,
    SupportsParseResultAssembler,
)
from dmsp_ssm._internal.pipeline.decoded_record import DecodedRecord
from dmsp_ssm._internal.pipeline.field_trace import FieldTrace
from dmsp_ssm.parse_result import ParseResult
from dmsp_ssm._internal.pipeline.raw_record import RawRecord
from dmsp_ssm._internal.validator.contracts import ValidationResult

pytestmark = pytest.mark.unit


def test_assembler_boundary_contract_exists_and_uses_bundle_input() -> None:
    hints = get_type_hints(
        SupportsParseResultAssembler.assemble,
        globalns=vars(assembler_contracts),
        localns=vars(assembler_contracts),
    )

    assert hints["bundle"] is ArtifactBundle
    assert hints["return"] is ParseResult


def test_artifact_bundle_contract_has_expected_fields_and_optional_artifacts() -> None:
    hints = get_type_hints(ArtifactBundle)

    assert hints["report"] is ValidationResult
    assert hints["raw_records"] == list[RawRecord] | None
    assert hints["decoded_records"] == list[DecodedRecord] | None
    assert hints["dataset"] == xr.Dataset | None
    assert hints["numpy_records"] == dict[str, np.ndarray] | None
    assert hints["table_records"] == list[dict[str, object]] | None
    assert hints["field_traces"] == list[FieldTrace] | None
    assert "metadata" in hints
    assert "extensions" in hints


def test_artifact_bundle_contract_does_not_contain_runtime_iteration_methods() -> None:
    bundle_fields = set(ArtifactBundle.__dataclass_fields__)
    assert bundle_fields == {
        "report",
        "raw_records",
        "decoded_records",
        "dataset",
        "numpy_records",
        "table_records",
        "field_traces",
        "metadata",
        "extensions",
    }
    assert not hasattr(ArtifactBundle, "emit")
    assert not hasattr(ArtifactBundle, "__next__")


def test_assembler_contract_isolated_from_parser_decoder_builder_runtime_logic() -> None:
    source_code = inspect.getsource(assembler_contracts)

    assert "parse_record" not in source_code
    assert "decode(" not in source_code
    assert ".build(" not in source_code


def test_assembler_contract_does_not_introduce_profile_runtime_logic() -> None:
    source_code = inspect.getsource(assembler_contracts)

    assert "class SSMXArray" not in source_code
    assert "class SSMNumpy" not in source_code
    assert "class SSMTable" not in source_code
    assert "class SSMRaw" not in source_code
