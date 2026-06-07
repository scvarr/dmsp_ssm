import pytest

from dmsp_ssm._internal.validator import (
    Validator,
    ValidationResult,
    ValidationIncident,
    ValidationErrorPolicy,
)

pytestmark = pytest.mark.unit


def build_valid_record(
    format_definition: dict,
    *,
    year: int = 2000,
    day_of_year: int = 100,
    flight_number: int = 10,
) -> bytes:
    record = bytearray(format_definition["record_size"])

    field_definitions = {
        field["name"]: field
        for section in ("header", "footer")
        for field in format_definition.get(section, [])
    }

    values = {
        "year": year,
        "day_of_year": day_of_year,
        "flight_number": flight_number,
    }

    for field_name, value in values.items():
        field = field_definitions[field_name]
        start = field["offset"]
        end = start + field["size"]
        record[start:end] = value.to_bytes(
            field["size"],
            byteorder=format_definition["byte_order"],
            signed=True,
        )

    return bytes(record)


def assert_context(
    context: dict | None,
    *,
    offset: int,
    year: int,
    day_of_year: int = 100,
    flight_number: int = 10,
) -> None:
    assert context is not None
    assert context["offset"] == offset
    assert context["validation_fields"]["year"] == year
    assert context["validation_fields"]["day_of_year"] == day_of_year
    assert context["validation_fields"]["flight_number"] == flight_number


def test_ssm_validator_accepts_raw_bytes(ssm_format_definition: dict) -> None:
    validator = Validator(format_definition=ssm_format_definition)

    result = validator.validate(b"raw-stream")

    assert isinstance(result, ValidationResult)


def test_ssm_validator_returns_validation_result(ssm_format_definition: dict) -> None:
    validator = Validator(format_definition=ssm_format_definition)

    result = validator.validate(b"")

    assert isinstance(result, ValidationResult)
    assert result.status == "ok"
    assert result.outcome == "nonfatal"
    assert result.validated_chunks == []
    assert result.incidents == []
    assert result.summary == {"candidate_record_count": 0}


def test_validation_incident_has_required_fields() -> None:
    incident = ValidationIncident(
        kind="invalid_record",
        start_offset=100,
        end_offset=1088,
        message="Р—Р°РїРёСЃСЊ РЅРµ РїСЂРѕС€Р»Р° РІР°Р»РёРґР°С†РёСЋ",
    )

    assert incident.kind == "invalid_record"
    assert incident.start_offset == 100
    assert incident.end_offset == 1088
    assert incident.message == "Р—Р°РїРёСЃСЊ РЅРµ РїСЂРѕС€Р»Р° РІР°Р»РёРґР°С†РёСЋ"

    #РљРѕРЅС‚РµРєСЃС‚ РѕРїС†РёРѕРЅР°Р»РµРЅ
    assert incident.previous_context is None
    assert incident.next_context is None


def test_ssm_validator_accepts_error_policy(ssm_format_definition: dict) -> None:
    validator = Validator(
        format_definition=ssm_format_definition,
        error_policy=ValidationErrorPolicy.RESYNC,
    )

    result = validator.validate(b"raw-stream")

    assert isinstance(result, ValidationResult)
    assert validator.error_policy == ValidationErrorPolicy.RESYNC


def test_ssm_validator_detects_invalid_record_by_required_fields_from_format_definition(ssm_format_definition: dict) -> None:

    validator = Validator(format_definition=ssm_format_definition)

    record = bytearray(ssm_format_definition["record_size"])

    year_field = validator.field_definitions["year"]
    day_field = validator.field_definitions["day_of_year"]
    flight_field = validator.field_definitions["flight_number"]

    record[
        year_field["offset"]:year_field["offset"] + year_field["size"]
    ] = (1900).to_bytes(year_field["size"], byteorder=validator.byte_order, signed=True)

    record[
        day_field["offset"]:day_field["offset"] + day_field["size"]
    ] = (100).to_bytes(day_field["size"], byteorder=validator.byte_order, signed=True)

    record[
        flight_field["offset"]:flight_field["offset"] + flight_field["size"]
    ] = (10).to_bytes(flight_field["size"], byteorder=validator.byte_order, signed=True)

    result = validator.validate(bytes(record))

    assert result.status == "error"
    assert len(result.incidents) == 1
    assert result.incidents[0].kind == "invalid_record"
    assert result.incidents[0].start_offset == 0
    assert result.incidents[0].end_offset == ssm_format_definition["record_size"]


def test_ssm_validator_accepts_valid_record_by_required_fields_from_format_definition(ssm_format_definition: dict) -> None:

    validator = Validator(format_definition=ssm_format_definition)

    record = bytearray(ssm_format_definition["record_size"])

    year_field = validator.field_definitions["year"]
    day_field = validator.field_definitions["day_of_year"]
    flight_field = validator.field_definitions["flight_number"]

    record[
        year_field["offset"]:year_field["offset"] + year_field["size"]
    ] = (2005).to_bytes(year_field["size"], byteorder=validator.byte_order, signed=True)

    record[
        day_field["offset"]:day_field["offset"] + day_field["size"]
    ] = (100).to_bytes(day_field["size"], byteorder=validator.byte_order, signed=True)

    record[
        flight_field["offset"]:flight_field["offset"] + flight_field["size"]
    ] = (10).to_bytes(flight_field["size"], byteorder=validator.byte_order, signed=True)

    result = validator.validate(bytes(record))

    assert result.status == "ok"
    assert result.validated_chunks == [bytes(record)]
    assert result.incidents == []


@pytest.mark.parametrize("field_name", ["year", "day_of_year", "flight_number"])
def test_ssm_validator_validates_required_fields_as_raw_values_without_transform(
    ssm_format_definition: dict,
    field_name: str,
) -> None:
    format_definition = {
        **ssm_format_definition,
        "header": [dict(field) for field in ssm_format_definition["header"]],
        "footer": [dict(field) for field in ssm_format_definition["footer"]],
    }

    for section_name in ("header", "footer"):
        for field in format_definition[section_name]:
            if field["name"] == field_name:
                field["transform"] = "float(i)/1000.0"

    validator = Validator(format_definition=format_definition)
    record = build_valid_record(ssm_format_definition, year=2000, day_of_year=100, flight_number=10)

    result = validator.validate(record)

    assert result.status == "ok"
    assert result.validated_chunks == [record]
    assert result.incidents == []


def test_ssm_validator_reports_candidate_record_count_for_clean_stream(ssm_format_definition: dict) -> None:

    validator = Validator(format_definition=ssm_format_definition)

    def build_valid_record(year: int) -> bytes:
        record = bytearray(ssm_format_definition["record_size"])
        record[0:4] = year.to_bytes(4, byteorder="big", signed=True)
        record[4:8] = (100).to_bytes(4, byteorder="big", signed=True)
        record[984:988] = (10).to_bytes(4, byteorder="big", signed=True)
        return bytes(record)

    raw_bytes = build_valid_record(2000) + build_valid_record(2001)

    result = validator.validate(raw_bytes)

    assert result.status == "ok"
    assert result.validated_chunks == [
        raw_bytes[0:ssm_format_definition["record_size"]],
        raw_bytes[ssm_format_definition["record_size"]:ssm_format_definition["record_size"] * 2],
    ]
    assert result.incidents == []
    assert result.summary == {"candidate_record_count": 2}


def test_ssm_validator_reports_trailing_bytes_as_error_in_strict_mode(
        ssm_format_definition: dict,
) -> None:
    validator = Validator(format_definition=ssm_format_definition)

    record = build_valid_record(ssm_format_definition, year=2000)
    raw_bytes = record + b"tail"

    result = validator.validate(raw_bytes)

    assert result.status == "error"
    assert result.outcome == "fatal"
    assert result.validated_chunks == [record]
    assert result.summary == {"candidate_record_count": 1}

    assert len(result.incidents) == 1
    assert result.incidents[0].kind == "trailing_bytes"
    assert result.incidents[0].start_offset == ssm_format_definition["record_size"]
    assert result.incidents[0].end_offset == ssm_format_definition["record_size"] + 4
    assert result.incidents[0].previous_context is None
    assert result.incidents[0].next_context is None
    assert result.incidents[0].estimated_missing_records is None


def test_ssm_validator_drops_trailing_bytes_in_resync_mode(
        ssm_format_definition: dict,
) -> None:
    validator = Validator(
        format_definition=ssm_format_definition,
        error_policy=ValidationErrorPolicy.RESYNC,
    )

    record = build_valid_record(ssm_format_definition, year=2000)
    raw_bytes = record + b"tail"

    result = validator.validate(raw_bytes)

    assert result.status == "ok"
    assert result.outcome == "nonfatal"
    assert result.validated_chunks == [record]
    assert result.summary == {"candidate_record_count": 1}

    assert len(result.incidents) == 1
    assert result.incidents[0].kind == "trailing_bytes"
    assert result.incidents[0].start_offset == ssm_format_definition["record_size"]
    assert result.incidents[0].end_offset == ssm_format_definition["record_size"] + 4


def test_ssm_validator_reports_invalid_record_as_error_in_strict_mode(
    ssm_format_definition: dict,
) -> None:
    validator = Validator(format_definition=ssm_format_definition)

    invalid_record = build_valid_record(ssm_format_definition, year=1900)

    result = validator.validate(invalid_record)

    assert result.status == "error"
    assert result.outcome == "fatal"
    assert result.validated_chunks == []
    assert result.summary["candidate_record_count"] == 1

    assert len(result.incidents) == 1
    assert result.incidents[0].kind == "invalid_record"
    assert result.incidents[0].start_offset == 0
    assert result.incidents[0].end_offset == ssm_format_definition["record_size"]


def test_ssm_validator_stops_after_invalid_record_in_strict_mode(
    ssm_format_definition: dict,
) -> None:
    validator = Validator(format_definition=ssm_format_definition)

    invalid_record = build_valid_record(ssm_format_definition, year=1900)
    second_invalid_record = build_valid_record(ssm_format_definition, year=1800)

    raw_bytes = invalid_record + second_invalid_record

    result = validator.validate(raw_bytes)

    assert result.status == "error"
    assert result.outcome == "fatal"
    assert result.validated_chunks == []
    assert result.summary["candidate_record_count"] == 2

    assert len(result.incidents) == 1
    assert result.incidents[0].kind == "invalid_record"
    assert result.incidents[0].start_offset == 0


def test_ssm_validator_continues_after_invalid_record_in_resync_mode(
    ssm_format_definition: dict,
) -> None:
    validator = Validator(
        format_definition=ssm_format_definition,
        error_policy=ValidationErrorPolicy.RESYNC,
    )

    invalid_record = build_valid_record(ssm_format_definition, year=1900)
    valid_record = build_valid_record(ssm_format_definition, year=2000)

    raw_bytes = invalid_record + valid_record

    result = validator.validate(raw_bytes)

    assert result.status == "ok"
    assert result.outcome == "nonfatal"
    assert result.validated_chunks == [valid_record]
    assert result.summary["candidate_record_count"] == 2

    assert len(result.incidents) == 1
    assert result.incidents[0].kind == "invalid_record"
    assert result.incidents[0].start_offset == 0
    assert result.incidents[0].end_offset == ssm_format_definition["record_size"]
    assert result.incidents[0].estimated_missing_records is None


def test_ssm_validator_invalid_record_attaches_previous_and_next_context(
    ssm_format_definition: dict,
) -> None:
    validator = Validator(
        format_definition=ssm_format_definition,
        error_policy=ValidationErrorPolicy.RESYNC,
    )

    valid_record_1 = build_valid_record(ssm_format_definition, year=2000)
    invalid_record = build_valid_record(ssm_format_definition, year=1900)
    valid_record_2 = build_valid_record(ssm_format_definition, year=2001)

    raw_bytes = valid_record_1 + invalid_record + valid_record_2

    result = validator.validate(raw_bytes)

    incident = next(
        incident for incident in result.incidents if incident.kind == "invalid_record"
    )
    record_size = ssm_format_definition["record_size"]
    assert_context(incident.previous_context, offset=0, year=2000)
    assert_context(incident.next_context, offset=record_size * 2, year=2001)
    assert incident.estimated_missing_records is None


def test_ssm_validator_invalid_record_has_empty_neighbors_on_stream_edges(
    ssm_format_definition: dict,
) -> None:
    validator = Validator(format_definition=ssm_format_definition)
    invalid_record = build_valid_record(ssm_format_definition, year=1900)

    result = validator.validate(invalid_record)

    incident = next(
        incident for incident in result.incidents if incident.kind == "invalid_record"
    )
    assert incident.previous_context is None
    assert incident.next_context is None
    assert incident.estimated_missing_records is None


def test_validation_incident_supports_desync_kind() -> None:
    incident = ValidationIncident(
        kind="desync",
        start_offset=100,
        end_offset=200,
        message="РџРѕС‚РµСЂСЏ СЃРёРЅС…СЂРѕРЅРёР·Р°С†РёРё РїРѕ РіСЂР°РЅРёС†Рµ Р·Р°РїРёСЃРё",
    )

    assert incident.kind == "desync"
    assert incident.start_offset == 100
    assert incident.end_offset == 200
    assert incident.message == "РџРѕС‚РµСЂСЏ СЃРёРЅС…СЂРѕРЅРёР·Р°С†РёРё РїРѕ РіСЂР°РЅРёС†Рµ Р·Р°РїРёСЃРё"


def test_ssm_validator_reports_desync_after_consecutive_invalid_records_in_resync_mode(
    ssm_format_definition: dict,
) -> None:
    validator = Validator(
        format_definition=ssm_format_definition,
        error_policy=ValidationErrorPolicy.RESYNC,
    )

    invalid_record_1 = build_valid_record(ssm_format_definition, year=1900)
    invalid_record_2 = build_valid_record(ssm_format_definition, year=1800)

    raw_bytes = invalid_record_1 + invalid_record_2

    result = validator.validate(raw_bytes)

    assert result.status == "error"
    assert result.outcome == "fatal"
    assert result.validated_chunks == []
    assert any(incident.kind == "desync" for incident in result.incidents)


def test_ssm_validator_resync_finds_next_valid_record_boundary_after_desync(
    ssm_format_definition: dict,
) -> None:
    validator = Validator(
        format_definition=ssm_format_definition,
        error_policy=ValidationErrorPolicy.RESYNC,
    )

    valid_record_1 = build_valid_record(ssm_format_definition, year=2000)
    valid_record_2 = build_valid_record(ssm_format_definition, year=2001)
    valid_record_3 = build_valid_record(ssm_format_definition, year=2002)

    corrupted_gap = b"\x00\x01\x02\x03\x04\x05\x06"

    raw_bytes = valid_record_1 + corrupted_gap + valid_record_2 + valid_record_3

    result = validator.validate(raw_bytes)

    assert result.status == "ok"
    assert result.outcome == "nonfatal"
    assert result.validated_chunks == [valid_record_1, valid_record_2, valid_record_3]
    assert any(incident.kind == "desync" for incident in result.incidents)

    desync_incident = next(
        incident for incident in result.incidents if incident.kind == "desync"
    )

    assert desync_incident.start_offset == ssm_format_definition["record_size"]
    assert desync_incident.end_offset == (
        ssm_format_definition["record_size"] + len(corrupted_gap)
    )
    assert_context(desync_incident.previous_context, offset=0, year=2000)
    assert_context(
        desync_incident.next_context,
        offset=ssm_format_definition["record_size"] + len(corrupted_gap),
        year=2001,
    )
    assert desync_incident.estimated_missing_records is None


def test_ssm_validator_resync_does_not_confirm_boundary_by_single_valid_record(
    ssm_format_definition: dict,
) -> None:
    validator = Validator(
        format_definition=ssm_format_definition,
        error_policy=ValidationErrorPolicy.RESYNC,
    )

    valid_record_1 = build_valid_record(ssm_format_definition, year=2000)
    valid_record_2 = build_valid_record(ssm_format_definition, year=2001)
    invalid_record = build_valid_record(ssm_format_definition, year=1900)

    corrupted_gap = b"\x00\x01\x02\x03\x04\x05\x06"

    raw_bytes = valid_record_1 + corrupted_gap + valid_record_2 + invalid_record

    result = validator.validate(raw_bytes)

    assert result.status == "error"
    assert result.outcome == "fatal"
    assert result.validated_chunks == [valid_record_1]
    desync_incident = next(
        incident for incident in result.incidents if incident.kind == "desync"
    )
    assert desync_incident.start_offset == ssm_format_definition["record_size"]
    assert desync_incident.end_offset == len(raw_bytes)
    assert_context(desync_incident.previous_context, offset=0, year=2000)
    assert desync_incident.next_context is None
    assert desync_incident.estimated_missing_records is None


def test_ssm_validator_estimates_missing_records_for_invalid_record_with_neighbors(
    ssm_format_definition: dict,
) -> None:
    validator = Validator(
        format_definition=ssm_format_definition,
        error_policy=ValidationErrorPolicy.RESYNC,
    )

    valid_record_1 = build_valid_record(
        ssm_format_definition,
        year=2000,
        flight_number=10,
    )
    invalid_record = build_valid_record(ssm_format_definition, year=1900)
    valid_record_2 = build_valid_record(
        ssm_format_definition,
        year=2000,
        flight_number=14,
    )

    raw_bytes = valid_record_1 + invalid_record + valid_record_2
    result = validator.validate(raw_bytes)
    assert result.outcome == "nonfatal"

    incident = next(
        incident for incident in result.incidents if incident.kind == "invalid_record"
    )
    assert incident.estimated_missing_records == 3


def test_ssm_validator_estimates_missing_records_for_desync_with_neighbors(
    ssm_format_definition: dict,
) -> None:
    validator = Validator(
        format_definition=ssm_format_definition,
        error_policy=ValidationErrorPolicy.RESYNC,
    )

    valid_record_1 = build_valid_record(
        ssm_format_definition,
        year=2000,
        flight_number=10,
    )
    valid_record_2 = build_valid_record(
        ssm_format_definition,
        year=2000,
        flight_number=15,
    )
    valid_record_3 = build_valid_record(
        ssm_format_definition,
        year=2000,
        flight_number=16,
    )

    corrupted_gap = b"\x00\x01\x02\x03\x04\x05\x06"
    raw_bytes = valid_record_1 + corrupted_gap + valid_record_2 + valid_record_3
    result = validator.validate(raw_bytes)
    assert result.outcome == "nonfatal"

    desync_incident = next(
        incident for incident in result.incidents if incident.kind == "desync"
    )
    assert desync_incident.estimated_missing_records == 4


def test_ssm_validator_does_not_estimate_missing_records_for_cross_year_neighbors(
    ssm_format_definition: dict,
) -> None:
    validator = Validator(
        format_definition=ssm_format_definition,
        error_policy=ValidationErrorPolicy.RESYNC,
    )

    valid_record_1 = build_valid_record(
        ssm_format_definition,
        year=2000,
        day_of_year=366,
        flight_number=20,
    )
    valid_record_2 = build_valid_record(
        ssm_format_definition,
        year=2001,
        day_of_year=1,
        flight_number=6,
    )
    valid_record_3 = build_valid_record(
        ssm_format_definition,
        year=2001,
        day_of_year=1,
        flight_number=7,
    )

    corrupted_gap = b"\x00\x01\x02\x03\x04\x05\x06"
    raw_bytes = valid_record_1 + corrupted_gap + valid_record_2 + valid_record_3
    result = validator.validate(raw_bytes)
    assert result.outcome == "nonfatal"

    desync_incident = next(
        incident for incident in result.incidents if incident.kind == "desync"
    )
    assert desync_incident.estimated_missing_records is None


@pytest.mark.parametrize("invalid_policy", ["unknown_policy", "drop_invalid"])
def test_ssm_validator_rejects_unknown_error_policy(
    ssm_format_definition: dict,
    invalid_policy: str,
) -> None:
    with pytest.raises(ValueError, match=invalid_policy):
        Validator(
            format_definition=ssm_format_definition,
            error_policy=invalid_policy,
        )


def test_ssm_validator_resync_does_not_confirm_boundary_at_stream_end(
    ssm_format_definition: dict,
) -> None:
    validator = Validator(
        format_definition=ssm_format_definition,
        error_policy=ValidationErrorPolicy.RESYNC,
    )

    valid_record_1 = build_valid_record(ssm_format_definition, year=2000)
    valid_record_2 = build_valid_record(ssm_format_definition, year=2001)
    corrupted_gap = b"\x00\x01\x02\x03\x04\x05\x06"
    raw_bytes = valid_record_1 + corrupted_gap + valid_record_2

    result = validator.validate(raw_bytes)

    assert result.status == "ok"
    assert result.outcome == "nonfatal"
    assert result.validated_chunks == [valid_record_1]
    assert any(incident.kind == "invalid_record" for incident in result.incidents)
    assert any(incident.kind == "trailing_bytes" for incident in result.incidents)
    assert all(incident.kind != "desync" for incident in result.incidents)


@pytest.mark.parametrize(
    "missing_field",
    ["year", "day_of_year", "flight_number"],
)
def test_ssm_validator_does_not_estimate_missing_records_when_context_field_missing(
    ssm_format_definition: dict,
    missing_field: str,
) -> None:
    validation_fields = [
        field
        for field in ssm_format_definition["validation_fields"]
        if field != missing_field
    ]
    format_definition = {
        **ssm_format_definition,
        "validation_fields": validation_fields,
    }

    validator = Validator(
        format_definition=format_definition,
        error_policy=ValidationErrorPolicy.RESYNC,
    )

    valid_record_1 = build_valid_record(ssm_format_definition, year=2000)
    valid_record_2 = build_valid_record(ssm_format_definition, year=2001)
    valid_record_3 = build_valid_record(ssm_format_definition, year=2002)
    corrupted_gap = b"\x00\x01\x02\x03\x04\x05\x06"
    raw_bytes = valid_record_1 + corrupted_gap + valid_record_2 + valid_record_3

    result = validator.validate(raw_bytes)
    desync_incident = next(
        incident for incident in result.incidents if incident.kind == "desync"
    )
    assert desync_incident.estimated_missing_records is None
