import pytest

pytestmark = pytest.mark.unit

TABLE_TRACE_REQUIRED_COLUMNS = {
    "record_index",
    "second_index",
    "section",
    "field_name",
    "field_role",
    "byte_offset",
    "byte_length",
    "raw_hex",
    "raw_int",
    "decoded_value",
    "normalized_value",
    "unit",
    "transform",
    "valid",
}


def test_table_trace_required_columns_set_matches_future_contract() -> None:
    assert TABLE_TRACE_REQUIRED_COLUMNS == {
        "record_index",
        "second_index",
        "section",
        "field_name",
        "field_role",
        "byte_offset",
        "byte_length",
        "raw_hex",
        "raw_int",
        "decoded_value",
        "normalized_value",
        "unit",
        "transform",
        "valid",
    }


def test_table_trace_contract_is_long_format_row_model_not_wide() -> None:
    assert "field_name" in TABLE_TRACE_REQUIRED_COLUMNS
    assert "raw_hex" in TABLE_TRACE_REQUIRED_COLUMNS
    assert "raw_int" in TABLE_TRACE_REQUIRED_COLUMNS
    assert "decoded_value" in TABLE_TRACE_REQUIRED_COLUMNS
    assert "normalized_value" in TABLE_TRACE_REQUIRED_COLUMNS

    forbidden_wide_columns = {
        "year_raw_hex",
        "bx_00_raw_hex",
        "time_decoded_value",
        "flight_number_normalized_value",
    }
    assert TABLE_TRACE_REQUIRED_COLUMNS.isdisjoint(forbidden_wide_columns)
