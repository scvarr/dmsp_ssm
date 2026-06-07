from __future__ import annotations

import pytest

from dmsp_ssm._internal.assembler import InMemoryParseResultAssembler
from dmsp_ssm._internal.builder import NumpyBuilder, TableBuilder, XArrayBuilder
from dmsp_ssm._internal.decoder import Decoder
from dmsp_ssm._internal.pipeline import RecordParser
from dmsp_ssm._internal.runtime.reader_runtime import (
    ReaderRuntime,
    create_reader_runtime,
)
from dmsp_ssm._internal.validator import Validator

pytestmark = pytest.mark.unit


def test_create_reader_runtime_contains_table_builder_and_existing_components() -> None:
    runtime = create_reader_runtime(validation_error_policy="strict")

    assert isinstance(runtime, ReaderRuntime)
    assert isinstance(runtime.validator, Validator)
    assert isinstance(runtime.record_parser, RecordParser)
    assert isinstance(runtime.decoder, Decoder)
    assert isinstance(runtime.builder, XArrayBuilder)
    assert isinstance(runtime.numpy_builder, NumpyBuilder)
    assert isinstance(runtime.table_builder, TableBuilder)
    assert isinstance(runtime.result_assembler, InMemoryParseResultAssembler)


def test_reader_runtime_reset_validator_keeps_behavior() -> None:
    runtime = create_reader_runtime(validation_error_policy="strict")
    before_validator = runtime.validator

    runtime.reset_validator(error_policy="resync")

    assert runtime.validator is not before_validator
    assert runtime.validator.error_policy == "resync"
