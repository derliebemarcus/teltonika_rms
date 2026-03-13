"""Unit tests for model normalization helpers."""

from __future__ import annotations

from datetime import UTC, datetime

from models import (
    first_value,
    has_location_coordinates,
    normalize_device,
    parse_float,
    parse_int,
    parse_online,
    parse_rms_timestamp,
)


def test_parse_rms_timestamp_utc() -> None:
    parsed = parse_rms_timestamp("2026-03-11 14:00:00")
    assert parsed is not None
    assert parsed.tzinfo == UTC


def test_parse_rms_timestamp_invalid_returns_none() -> None:
    assert parse_rms_timestamp(None) is None
    assert parse_rms_timestamp("not-a-date") is None


def test_has_location_coordinates_false_without_coords() -> None:
    normalized = normalize_device({"id": "a1", "name": "Router A"})
    assert normalized is not None
    assert has_location_coordinates(normalized) is False


def test_has_location_coordinates_true_with_coords() -> None:
    normalized = normalize_device(
        {"id": "a1", "name": "Router A"},
        state={"online": True},
        location={"latitude": "54.1", "longitude": "25.2"},
    )
    assert normalized is not None
    assert has_location_coordinates(normalized) is True


def test_normalize_device_parses_lat_lng_and_location_label() -> None:
    normalized = normalize_device(
        {"id": "a1", "name": "Router A"},
        location={"lat": "54.1234", "lng": "25.5678", "address": "Vilnius, LT"},
    )
    assert normalized is not None
    assert normalized.latitude == 54.1234
    assert normalized.longitude == 25.5678
    assert normalized.location_label == "Vilnius, LT"


def test_normalize_device_parses_geojson_coordinates() -> None:
    normalized = normalize_device(
        {"id": "a1", "name": "Router A"},
        location={"coordinates": [25.5678, 54.1234]},
    )
    assert normalized is not None
    assert normalized.latitude == 54.1234
    assert normalized.longitude == 25.5678
    assert normalized.location_label == "54.123400, 25.567800"


def test_model_helper_functions_cover_common_variants() -> None:
    payload = {"a": {"b": "value"}, "serial": "SER-1"}
    assert first_value(payload, "a.b", "serial") == "value"
    assert first_value(payload, "missing", "serial") == "SER-1"

    assert parse_online(True) is True
    assert parse_online(1) is True
    assert parse_online("offline") is False
    assert parse_online("unknown") is None

    assert parse_float("1.25") == 1.25
    assert parse_float("bad") is None
    assert parse_int("7") == 7
    assert parse_int("bad") is None


def test_normalize_device_handles_missing_id_datetime_and_string_coordinates() -> None:
    assert normalize_device({"name": "No ID"}) is None

    naive = datetime(2026, 3, 13, 12, 0)
    normalized = normalize_device(
        {"serial": "SER-1"},
        state={"status": "online", "updated_at": naive},
        location={"coordinates": "8.55,47.37"},
    )

    assert normalized is not None
    assert normalized.device_id == "SER-1"
    assert normalized.name == "RMS SER-1"
    assert normalized.online is True
    assert normalized.last_seen == naive.replace(tzinfo=UTC)
    assert normalized.clients_count is None
    assert normalized.router_uptime is None
    assert normalized.latitude == 47.37
    assert normalized.longitude == 8.55
    assert normalized.location_label == "47.370000, 8.550000"


def test_normalize_device_parses_optional_runtime_metrics() -> None:
    normalized = normalize_device(
        {"id": "a1", "clients_count": "3"},
        state={
            "router_uptime": 7200,
            "signal": "-79",
            "wan_state": "Mobile",
            "connection_state": "connected",
            "connection_type": "LTE",
            "sim_slot": "2",
        },
    )

    assert normalized is not None
    assert normalized.clients_count == 3
    assert normalized.router_uptime == 7200
    assert normalized.signal_strength == -79
    assert normalized.wan_state == "Mobile"
    assert normalized.connection_state == "connected"
    assert normalized.connection_type == "LTE"
    assert normalized.sim_slot == 2
