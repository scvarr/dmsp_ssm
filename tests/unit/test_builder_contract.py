import inspect
from typing import get_type_hints

import pytest

import dmsp_ssm._internal.builder.contracts as builder_contracts
from dmsp_ssm._internal.builder import (
    BuilderArtifact,
    SupportsDecodedRecordBuilder,
)
from dmsp_ssm._internal.pipeline import DecodedRecord

pytestmark = pytest.mark.unit


def test_builder_contract_accepts_only_decoded_record_list() -> None:
    hints = get_type_hints(
        SupportsDecodedRecordBuilder.build,
        globalns=vars(builder_contracts),
        localns=vars(builder_contracts),
    )

    assert hints["records"] == list[DecodedRecord]
    assert hints["return"] is BuilderArtifact


def test_builder_contract_does_not_depend_on_raw_layer_symbols() -> None:
    source_code = inspect.getsource(builder_contracts)

    assert "RawRecord" not in source_code
