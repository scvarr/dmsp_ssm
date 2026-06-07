from __future__ import annotations

import inspect

import numpy as np
import pytest
import xarray as xr

from dmsp_ssm._internal.assembler import ArtifactBundle
from dmsp_ssm._internal.assembler import (
    InMemoryParseResultAssembler,
)
from dmsp_ssm.parse_result import ParseResult
from dmsp_ssm._internal.validator import ValidationResult

pytestmark = pytest.mark.unit


def _build_dataset() -> xr.Dataset:
    return xr.Dataset(
        data_vars={
            "time": (("record", "second"), [[1.0]]),
            "bx": (("record", "second"), [[2.0]]),
            "by": (("record", "second"), [[3.0]]),
            "bz": (("record", "second"), [[4.0]]),
            "valid": (("record", "second"), [[True]]),
            "flight_number": ("record", [1]),
            "year": ("record", [2024]),
            "day_of_year": ("record", [100]),
            "minute_start_sec_of_day": ("record", [60]),
            "latitude_deg": ("record", [10.0]),
            "longitude_deg": ("record", [20.0]),
            "altitude_km": ("record", [500.0]),
        },
        coords={
            "record_time": ("record", [0]),
            "second_index": ("second", [0]),
        },
        attrs={
            "builder": "xarray",
            "pipeline_terminal_stage": "builder",
            "record_dimension": "record",
            "second_dimension": "second",
        },
    )


def test_in_memory_assembler_returns_parse_result_from_bundle_dataset() -> None:
    assembler = InMemoryParseResultAssembler()
    dataset = _build_dataset()
    report = ValidationResult(status="ok", validated_chunks=[])
    bundle = ArtifactBundle(
        report=report,
        dataset=dataset,
        metadata={"source": "unit"},
        extensions={"trace": "t1"},
    )

    result = assembler.assemble(bundle)

    assert isinstance(result, ParseResult)
    assert result.records is dataset
    assert result.report is report
    assert result.metadata == {"source": "unit"}
    assert result.extensions == {"trace": "t1"}


def test_in_memory_assembler_fails_fast_when_dataset_absent() -> None:
    assembler = InMemoryParseResultAssembler()
    bundle = ArtifactBundle(
        report=ValidationResult(status="ok", validated_chunks=[]),
        dataset=None,
        numpy_records=None,
        table_records=None,
    )

    with pytest.raises(
        ValueError,
        match="Для in-memory assembler требуется dataset, numpy_records или table_records в artifact bundle.",
    ):
        assembler.assemble(bundle)


def test_in_memory_assembler_returns_parse_result_from_bundle_numpy_records() -> None:
    assembler = InMemoryParseResultAssembler()
    report = ValidationResult(status="ok", validated_chunks=[])
    numpy_records = {
        "time": np.array([[1.0]]),
        "bx": np.array([[2.0]]),
        "by": np.array([[3.0]]),
        "bz": np.array([[4.0]]),
        "valid": np.array([[True]]),
        "flight_number": np.array([1]),
        "year": np.array([2024]),
        "day_of_year": np.array([100]),
        "minute_start_sec_of_day": np.array([60]),
        "latitude_deg": np.array([10.0]),
        "longitude_deg": np.array([20.0]),
        "altitude_km": np.array([500.0]),
    }
    bundle = ArtifactBundle(
        report=report,
        dataset=None,
        numpy_records=numpy_records,
    )

    result = assembler.assemble(bundle)

    assert isinstance(result, ParseResult)
    assert result.records is numpy_records
    assert result.report is report


def test_in_memory_assembler_returns_parse_result_from_bundle_table_records() -> None:
    assembler = InMemoryParseResultAssembler()
    report = ValidationResult(status="ok", validated_chunks=[])
    table_records = [
        {
            "record_index": 0,
            "second_index": None,
            "section": "header",
            "field_name": "year",
            "field_role": "record",
            "byte_offset": 0,
            "byte_length": 4,
            "raw_hex": "000007E8",
            "raw_int": 2024,
            "decoded_value": 2024,
            "normalized_value": 2024,
            "unit": None,
            "transform": None,
            "valid": True,
        }
    ]
    bundle = ArtifactBundle(
        report=report,
        dataset=None,
        numpy_records=None,
        table_records=table_records,
    )

    result = assembler.assemble(bundle)

    assert isinstance(result, ParseResult)
    assert result.records is table_records
    assert result.report is report


def test_in_memory_assembler_prefers_dataset_and_numpy_over_table_records() -> None:
    assembler = InMemoryParseResultAssembler()
    report = ValidationResult(status="ok", validated_chunks=[])
    dataset = _build_dataset()
    numpy_records = {"time": np.array([[1.0]])}
    table_records = [{"field_name": "year"}]

    bundle = ArtifactBundle(
        report=report,
        dataset=dataset,
        numpy_records=numpy_records,
        table_records=table_records,
    )

    result = assembler.assemble(bundle)

    assert result.records is dataset


def test_in_memory_assembler_has_no_pipeline_execution_logic() -> None:
    source_code = inspect.getsource(InMemoryParseResultAssembler)

    assert "parse_record" not in source_code
    assert "decode(" not in source_code
    assert ".build(" not in source_code
