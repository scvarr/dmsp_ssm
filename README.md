# dmsp-ssm

`dmsp-ssm` is a Python library for reading, validating, and converting DMSP SSM binary data files.

The package accepts single `.dat` files, gzip-compressed `.gz` files, and directories of supported files. It returns a `ParseResult` with parsed records and a validation report. The default output is an `xarray.Dataset`.

## Installation

```bash
pip install dmsp-ssm
```

For local development:

```bash
pip install -e .[dev]
```

## Quick Start

```python
from dmsp_ssm import Reader

reader = Reader()
result = reader.parse("path/to/file_or_directory")

dataset = result.records
report = result.report

print(dataset)
print(report.summary)
```

## Output Profiles

Select an output profile with `ParseOptions`:

```python
from dmsp_ssm import ParseOptions, Reader

reader = Reader()
result = reader.parse(
    "path/to/data",
    options=ParseOptions(output_profile="xarray"),
)
```

Supported profiles:

- `xarray`: returns an `xarray.Dataset` with `record` and `second` dimensions.
- `numpy`: returns a `dict[str, numpy.ndarray]`.
- `table`: returns long-format trace rows as `list[dict[str, object]]`.

## xarray Output

The default `xarray` profile contains:

- dimensions: `record`, `second`
- coordinates: `record_time`, `second_index`
- second-level variables: `time`, `bx`, `by`, `bz`, `valid`
- record-level variables: `flight_number`, `year`, `day_of_year`, `minute_start_sec_of_day`, `latitude_deg`, `longitude_deg`, `altitude_km`

Data variables include `units` attributes when units are defined by the internal format definition.

Missing second-level measurements are detected by the `time == -1000.0` marker. For those positions, `time`, `bx`, `by`, and `bz` are normalized to `NaN`, and `valid` is set to `False`.

## Validation Report

`ParseResult.report` contains validation status, incidents, and summary counters:

```python
result = Reader().parse("path/to/data")

print(result.report.status)
print(result.report.outcome)
print(result.report.summary)
```

To include compact missing-minute ranges:

```python
result = Reader().parse(
    "path/to/data",
    include_missing_minute_ranges=True,
)
```

For directory inputs, the summary can also include per-file missing-minute diagnostics in `missing_minute_ranges_by_file`.

## API Overview

### Reader

```python
Reader(
    error_policy="resync",
    pre_parse_size_warning_threshold_bytes=256 * 1024 * 1024,
)
```

Use `Reader.parse(path, ...)` to parse a file or directory.

### ParseOptions

```python
ParseOptions(
    recursive=True,
    error_policy=None,
    include_missing_minute_ranges=False,
    output_profile="xarray",
)
```

`output_profile` must be one of `xarray`, `numpy`, or `table`.

### ParseResult

`ParseResult.records` contains the selected output artifact.

`ParseResult.report` contains validation diagnostics.

`ParseResult.metadata` and `ParseResult.extensions` are reserved for optional metadata.

## Supported Input

- `.dat` files
- `.gz` files containing DMSP SSM binary data
- directories containing only one supported file type
- recursive directory traversal when `recursive=True`

Directories containing mixed `.dat` and `.gz` files are rejected.

## License

This project is licensed under the MIT License.
