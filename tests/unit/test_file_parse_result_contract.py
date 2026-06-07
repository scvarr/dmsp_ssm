from pathlib import Path

import pytest

from dmsp_ssm._internal.orchestration.file_parse_result import FileParseResult
from dmsp_ssm._internal.source.data_source import SourceFile
from dmsp_ssm._internal.pipeline.field_trace import FieldTrace
from dmsp_ssm._internal.pipeline.raw_record import RawRecord

pytestmark = pytest.mark.unit


def test_file_parse_result_contains_source_file_records_and_report() -> None:
    source_file = SourceFile(path=Path("sample.dat"), kind="dat")
    record = RawRecord(raw_bytes=b"record", header={}, blocks={}, footer={})
    report = {"validated_chunks": [b"record"], "status": "ok"}

    result = FileParseResult(
        source_file=source_file,
        records=[record],
        field_traces=[
            FieldTrace(
                record_index=0,
                second_index=None,
                section="header",
                field_name="year",
                field_role="record",
                byte_offset=0,
                byte_length=4,
                raw_hex="000007E5",
                raw_int=2021,
                unit=None,
                transform=None,
            )
        ],
        report=report,
    )

    assert result.source_file is source_file
    assert result.records == [record]
    assert result.field_traces
    assert result.report is report


def test_file_parse_result_is_internal_not_public_package_export() -> None:
    import dmsp_ssm

    assert "FileParseResult" not in dmsp_ssm.__all__
    assert not hasattr(dmsp_ssm, "FileParseResult")
