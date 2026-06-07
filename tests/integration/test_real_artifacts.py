import gzip
import shutil
from collections import Counter
from pathlib import Path

import pytest
import xarray as xr

from dmsp_ssm._internal.source.data_source import DataSource
from dmsp_ssm.parse_options import ParseOptions
from dmsp_ssm.parse_result import ParseResult
from dmsp_ssm.reader import Reader
from dmsp_ssm._internal.validator.contracts import ValidationResult
from dmsp_ssm._internal.validator.policy import ValidationErrorPolicy

pytestmark = pytest.mark.integration

FROZEN_SECOND_LEVEL_VARS = {"time", "bx", "by", "bz", "valid"}
FROZEN_RECORD_LEVEL_VARS = {
    "flight_number",
    "year",
    "day_of_year",
    "minute_start_sec_of_day",
    "latitude_deg",
    "longitude_deg",
    "altitude_km",
}
FROZEN_DATA_VARS = FROZEN_SECOND_LEVEL_VARS | FROZEN_RECORD_LEVEL_VARS


def _read_file_bytes(path: Path) -> bytes:
    with path.open("rb") as stream:
        return stream.read()


def _read_all_source_bytes(source: DataSource) -> bytes:
    source_files = source.list_source_files()
    return b"".join(source.read_source_file(source_file) for source_file in source_files)


def test_data_source_reads_real_dat_file(tests_data_dir: Path) -> None:
    dat_path = tests_data_dir / "m1508275.dat"

    source = DataSource(dat_path)

    assert _read_all_source_bytes(source) == _read_file_bytes(dat_path)


def test_data_source_reads_real_gz_file_as_uncompressed_bytes(tests_data_dir: Path) -> None:
    gz_path = tests_data_dir / "m1508275.dat.gz"

    source = DataSource(gz_path)

    with gzip.open(gz_path, "rb") as stream:
        expected = stream.read()

    assert _read_all_source_bytes(source) == expected


def test_reader_parse_reads_real_file_through_default_data_source(
    tests_data_dir: Path,
) -> None:
    dat_path = tests_data_dir / "m1508275.dat"
    reader = Reader()

    result = reader.parse(dat_path)

    assert isinstance(result, ParseResult)
    assert isinstance(result.records, xr.Dataset)
    assert result.records.sizes["record"] == 1440
    assert result.records.sizes["second"] == 60
    assert "record_time" in result.records.coords
    assert "second_index" in result.records.coords
    assert set(result.records.data_vars) == FROZEN_DATA_VARS


def test_data_source_reads_real_corrupted_tail_artifact(tests_data_dir: Path) -> None:
    corrupted_path = tests_data_dir / "corrupted_incomplete_tail.dat"

    source = DataSource(corrupted_path)

    assert _read_all_source_bytes(source) == _read_file_bytes(corrupted_path)


def test_data_source_raises_for_real_mixed_directory(
    tests_data_dir: Path,
    tmp_path: Path,
) -> None:
    fixture_dir = tmp_path / "mixed"
    fixture_dir.mkdir()

    shutil.copy2(tests_data_dir / "m1508275.dat", fixture_dir / "a.dat")
    shutil.copy2(tests_data_dir / "m1508275.dat.gz", fixture_dir / "b.gz")

    source = DataSource(fixture_dir)

    with pytest.raises(ValueError):
        source.list_source_files()


def test_reader_parse_reports_corrupted_middle_artifact_in_strict_mode(
    tests_data_dir: Path,
) -> None:
    corrupted_path = tests_data_dir / "corrupted.dat"
    reader = Reader()

    result = reader.parse(
        corrupted_path,
        options=ParseOptions(
            recursive=False,
            error_policy=ValidationErrorPolicy.STRICT,
        ),
    )

    assert isinstance(result, ParseResult)
    assert isinstance(result.records, xr.Dataset)
    assert result.records.sizes["record"] == 720
    assert set(result.records.data_vars) == FROZEN_DATA_VARS

    report = result.report
    assert isinstance(report, ValidationResult)
    assert report.status == "error"
    assert report.outcome == "fatal"
    assert report.summary["candidate_record_count"] == 1372
    assert report.summary["expected_record_count"] == 1440
    assert report.summary["missing_record_count"] == 720
    assert report.summary["has_missing_records"] is True
    assert report.validated_chunks == []
    assert len(report.incidents) == 1
    assert report.incidents[0].kind == "invalid_record"


def test_reader_parse_reports_corrupted_middle_artifact_in_resync_mode(
    tests_data_dir: Path,
) -> None:
    corrupted_path = tests_data_dir / "corrupted.dat"
    reader = Reader()

    result = reader.parse(
        corrupted_path,
        options=ParseOptions(
            recursive=False,
            error_policy=ValidationErrorPolicy.RESYNC,
        ),
    )

    assert isinstance(result, ParseResult)
    assert isinstance(result.records, xr.Dataset)
    assert result.records.sizes["record"] == 1371
    assert set(result.records.data_vars) == FROZEN_DATA_VARS

    report = result.report
    assert isinstance(report, ValidationResult)
    assert report.status == "ok"
    assert report.outcome == "nonfatal"
    assert report.summary["candidate_record_count"] == 1372
    assert report.summary["expected_record_count"] == 1440
    assert report.summary["missing_record_count"] == 69
    assert report.summary["has_missing_records"] is True
    assert report.validated_chunks == []
    assert len(report.incidents) == 3
    assert Counter(incident.kind for incident in report.incidents) == {
        "desync": 2,
        "trailing_bytes": 1,
    }


def test_reader_parse_directory_aggregates_parse_result_for_multiple_valid_files(
    tests_data_dir: Path,
    tmp_path: Path,
) -> None:
    fixture_dir = tmp_path / "multi-valid"
    fixture_dir.mkdir()

    shutil.copy2(tests_data_dir / "m1508275.dat", fixture_dir / "a.dat")
    shutil.copy2(tests_data_dir / "m1508275.dat", fixture_dir / "b.dat")

    reader = Reader()
    result = reader.parse(fixture_dir)

    assert isinstance(result, ParseResult)
    assert isinstance(result.records, xr.Dataset)
    assert result.records.sizes["record"] == 2880
    assert set(result.records.data_vars) == FROZEN_DATA_VARS

    report = result.report
    assert isinstance(report, ValidationResult)
    assert report.status == "ok"
    assert report.outcome == "nonfatal"
    assert report.summary["file_count"] == 2
    assert report.summary["file_error_count"] == 0
    assert report.summary["candidate_record_count"] == 2880
    assert report.summary["validated_record_count"] == 2880
    assert report.summary["expected_record_count"] == 2880
    assert report.summary["missing_record_count"] == 0
    assert report.summary["has_missing_records"] is False
    assert report.validated_chunks == []
    assert len(report.incidents) == 0


def test_reader_parse_directory_aggregates_reports_for_valid_and_corrupted_files_in_strict_mode(
    tests_data_dir: Path,
    tmp_path: Path,
) -> None:
    fixture_dir = tmp_path / "multi-mixed-quality"
    fixture_dir.mkdir()

    shutil.copy2(tests_data_dir / "m1508275.dat", fixture_dir / "a_valid.dat")
    shutil.copy2(tests_data_dir / "corrupted.dat", fixture_dir / "b_corrupted.dat")

    reader = Reader()
    result = reader.parse(
        fixture_dir,
        options=ParseOptions(error_policy=ValidationErrorPolicy.STRICT),
        include_missing_minute_ranges=True,
    )

    assert isinstance(result, ParseResult)
    assert isinstance(result.records, xr.Dataset)
    assert result.records.sizes["record"] == 2160
    assert set(result.records.data_vars) == FROZEN_DATA_VARS

    report = result.report
    assert isinstance(report, ValidationResult)
    assert report.status == "error"
    assert report.outcome == "fatal"
    assert report.summary["file_count"] == 2
    assert report.summary["file_error_count"] == 1
    assert report.summary["candidate_record_count"] == 2812
    assert report.summary["validated_record_count"] == 2160
    assert report.summary["expected_record_count"] == 2880
    assert report.summary["missing_record_count"] == 720
    assert report.summary["has_missing_records"] is True
    ranges_by_file = report.summary["missing_minute_ranges_by_file"]
    assert ranges_by_file[0] == {
        "source_file": "a_valid.dat",
        "expected_record_count": 1440,
        "observed_record_count": 1440,
        "missing_record_count": 0,
        "has_missing_records": False,
        "first_minute_index": 0,
        "last_minute_index": 1439,
        "gap_count": 0,
        "missing_minute_ranges": [],
    }
    corrupted_file_summary = ranges_by_file[1]
    assert corrupted_file_summary["source_file"] == "b_corrupted.dat"
    assert corrupted_file_summary["expected_record_count"] == 1440
    assert corrupted_file_summary["observed_record_count"] == 720
    assert corrupted_file_summary["missing_record_count"] == 720
    assert corrupted_file_summary["has_missing_records"] is True
    assert corrupted_file_summary["first_minute_index"] == 0
    assert corrupted_file_summary["last_minute_index"] == 739
    assert corrupted_file_summary["gap_count"] == 20
    assert sum(
        missing_range["count"]
        for missing_range in corrupted_file_summary["missing_minute_ranges"]
    ) == 720
    assert report.validated_chunks == []
    assert len(report.incidents) == 1
    assert report.incidents[0].kind == "invalid_record"
