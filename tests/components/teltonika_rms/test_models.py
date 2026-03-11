"""Unit tests for model normalization helpers."""

from __future__ import annotations

from datetime import UTC

from models import has_location_coordinates, normalize_device, parse_rms_timestamp


def test_parse_rms_timestamp_utc() -> None:
    parsed = parse_rms_timestamp("2026-03-11 14:00:00")
    assert parsed is not None
    assert parsed.tzinfo == UTC


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
