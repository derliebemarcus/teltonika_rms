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
