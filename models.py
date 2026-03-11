"""Data normalization helpers for Teltonika RMS responses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

RMS_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass(slots=True)
class NormalizedDevice:
    """A normalized representation of an RMS device."""

    device_id: str
    name: str
    model: str | None
    firmware: str | None
    serial: str | None
    online: bool | None
    last_seen: datetime | None
    latitude: float | None
    longitude: float | None
    raw: dict[str, Any]


def parse_rms_timestamp(value: str | None) -> datetime | None:
    """Parse RMS UTC timestamps in Y-m-d H:i:s format."""
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, RMS_TIMESTAMP_FORMAT)
    except ValueError:
        return None
    return parsed.replace(tzinfo=UTC)


def _walk_path(payload: dict[str, Any], path: str) -> Any:
    cursor: Any = payload
    for part in path.split("."):
        if not isinstance(cursor, dict) or part not in cursor:
            return None
        cursor = cursor[part]
    return cursor


def first_value(payload: dict[str, Any], *paths: str) -> Any:
    """Return the first non-empty value from a list of candidate paths."""
    for path in paths:
        value = _walk_path(payload, path)
        if value not in (None, "", []):
            return value
    return None


def parse_online(value: Any) -> bool | None:
    """Convert varied online status values to bool."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"online", "up", "connected", "true", "1"}:
            return True
        if lowered in {"offline", "down", "disconnected", "false", "0"}:
            return False
    return None


def parse_float(value: Any) -> float | None:
    """Convert values to float when possible."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_device(
    inventory: dict[str, Any],
    state: dict[str, Any] | None = None,
    location: dict[str, Any] | None = None,
) -> NormalizedDevice | None:
    """Build a stable normalized device object from RMS payload fragments."""
    merged: dict[str, Any] = {}
    merged.update(inventory or {})
    if state:
        merged.update(state)
    if location:
        merged["location"] = location

    device_id = first_value(
        merged,
        "id",
        "device_id",
        "deviceId",
        "serial",
        "imei",
    )
    if device_id is None:
        return None
    device_id_str = str(device_id)

    name = first_value(merged, "name", "title", "hostname", "device_name") or f"RMS {device_id_str}"

    model = first_value(merged, "model", "product.model", "hardware.model")
    firmware = first_value(merged, "firmware", "fw_version", "software.version")
    serial = first_value(merged, "serial", "serial_number", "sn")

    online = parse_online(
        first_value(merged, "online", "status", "connection.online", "state.online")
    )

    last_seen_raw = first_value(
        merged,
        "last_seen",
        "lastSeen",
        "last_update",
        "updated_at",
        "timestamp",
    )
    if isinstance(last_seen_raw, datetime):
        last_seen = last_seen_raw if last_seen_raw.tzinfo else last_seen_raw.replace(tzinfo=UTC)
    else:
        last_seen = parse_rms_timestamp(str(last_seen_raw)) if last_seen_raw else None

    latitude = parse_float(
        first_value(merged, "location.latitude", "latitude", "gps.latitude", "lat")
    )
    longitude = parse_float(
        first_value(merged, "location.longitude", "longitude", "gps.longitude", "lon", "lng")
    )

    return NormalizedDevice(
        device_id=device_id_str,
        name=str(name),
        model=str(model) if model is not None else None,
        firmware=str(firmware) if firmware is not None else None,
        serial=str(serial) if serial is not None else None,
        online=online,
        last_seen=last_seen,
        latitude=latitude,
        longitude=longitude,
        raw=merged,
    )
