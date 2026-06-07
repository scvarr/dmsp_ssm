from __future__ import annotations

from dataclasses import dataclass

import pytest

from dmsp_ssm._internal.validator.validation_report_adapter import (
    extract_validated_chunks,
    strip_validated_chunks_for_facade,
)

pytestmark = pytest.mark.unit


@dataclass
class _ReportWithChunks:
    validated_chunks: object
    summary: dict[str, int]


def test_extract_validated_chunks_accepts_dict_with_bytes_list() -> None:
    report = {"validated_chunks": [b"a", b"b"]}

    chunks = extract_validated_chunks(validation_report=report)

    assert chunks == [b"a", b"b"]


def test_extract_validated_chunks_raises_when_chunks_missing() -> None:
    with pytest.raises(ValueError, match="отсутствует validated_chunks"):
        extract_validated_chunks(validation_report={"summary": {"count": 1}})


def test_extract_validated_chunks_raises_when_chunks_not_list() -> None:
    report = _ReportWithChunks(validated_chunks=(b"a",), summary={"count": 1})

    with pytest.raises(
        ValueError,
        match="validated_chunks должен быть списком bytes",
    ):
        extract_validated_chunks(validation_report=report)


def test_extract_validated_chunks_raises_when_list_contains_non_bytes() -> None:
    report = {"validated_chunks": [b"a", "bad"]}

    with pytest.raises(
        ValueError,
        match="validated_chunks должен быть списком bytes",
    ):
        extract_validated_chunks(validation_report=report)


def test_strip_validated_chunks_for_facade_removes_only_target_key_from_dict() -> None:
    report = {"validated_chunks": [b"a"], "summary": {"count": 1}, "status": "ok"}

    result = strip_validated_chunks_for_facade(report=report)

    assert result is report
    assert "validated_chunks" not in result
    assert result["summary"] == {"count": 1}
    assert result["status"] == "ok"


def test_strip_validated_chunks_for_facade_sets_empty_list_on_object() -> None:
    report = _ReportWithChunks(validated_chunks=[b"a"], summary={"count": 1})

    result = strip_validated_chunks_for_facade(report=report)

    assert result is report
    assert report.validated_chunks == []
    assert report.summary == {"count": 1}
