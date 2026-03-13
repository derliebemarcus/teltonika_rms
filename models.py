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
    latest_firmware: str | None
    stable_firmware: str | None
    firmware_update_available: bool | None
    serial: str | None
    online: bool | None
    last_seen: datetime | None
    clients_count: int | None
    router_uptime: int | None
    temperature: int | None
    signal_strength: int | None
    wan_state: str | None
    connection_state: str | None
    connection_type: str | None
    sim_slot: int | None
    latitude: float | None
    longitude: float | None
    location_label: str | None
    raw: dict[str, Any]


def has_location_coordinates(device: NormalizedDevice | None) -> bool:
    """Return True when a normalized device has usable GPS coordinates."""
    if device is None:
        return False
    return device.latitude is not None and device.longitude is not None


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


def parse_int(value: Any) -> int | None:
    """Convert values to int when possible."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_coordinate_pair(value: Any) -> tuple[float | None, float | None]:
    """Parse coordinates in common tuple/list/string formats.

    Returns `(latitude, longitude)` when possible.
    """
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        # GeoJSON uses [longitude, latitude].
        longitude = parse_float(value[0])
        latitude = parse_float(value[1])
        return latitude, longitude
    if isinstance(value, str) and "," in value:
        lon_raw, lat_raw = value.split(",", maxsplit=1)
        latitude = parse_float(lat_raw.strip())
        longitude = parse_float(lon_raw.strip())
        return latitude, longitude
    return None, None


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
    latest_firmware = first_value(merged, "firmware_information.latest.name")
    stable_firmware = first_value(merged, "firmware_information.stable.name")
    serial = first_value(merged, "serial", "serial_number", "sn")
    comparison_firmware = latest_firmware or stable_firmware
    firmware_update_available = None
    if firmware is not None and comparison_firmware is not None:
        firmware_update_available = str(firmware) != str(comparison_firmware)

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

    clients_count = parse_int(first_value(merged, "clients_count"))
    router_uptime = parse_int(first_value(merged, "router_uptime"))
    temperature = parse_int(first_value(merged, "temperature"))
    signal_strength = parse_int(first_value(merged, "signal"))
    sim_slot = parse_int(first_value(merged, "sim_slot"))
    wan_state_raw = first_value(merged, "wan_state")
    connection_state_raw = first_value(merged, "connection_state")
    connection_type_raw = first_value(merged, "connection_type")

    latitude = parse_float(
        first_value(
            merged,
            "location.latitude",
            "location.lat",
            "location.coords.latitude",
            "latitude",
            "gps.latitude",
            "lat",
        )
    )
    longitude = parse_float(
        first_value(
            merged,
            "location.longitude",
            "location.lon",
            "location.lng",
            "location.coords.longitude",
            "longitude",
            "gps.longitude",
            "lon",
            "lng",
        )
    )
    if latitude is None or longitude is None:
        list_latitude, list_longitude = _parse_coordinate_pair(
            first_value(
                merged,
                "location.coordinates",
                "gps.coordinates",
                "coordinates",
            )
        )
        if latitude is None:
            latitude = list_latitude
        if longitude is None:
            longitude = list_longitude

    location_label_raw = first_value(
        merged,
        "location.address",
        "location.address.formatted",
        "location.formatted",
        "location.name",
        "address",
        "gps.address",
    )
    location_label = str(location_label_raw) if location_label_raw is not None else None
    if location_label is None and latitude is not None and longitude is not None:
        location_label = f"{latitude:.6f}, {longitude:.6f}"

    return NormalizedDevice(
        device_id=device_id_str,
        name=str(name),
        model=str(model) if model is not None else None,
        firmware=str(firmware) if firmware is not None else None,
        latest_firmware=str(latest_firmware) if latest_firmware is not None else None,
        stable_firmware=str(stable_firmware) if stable_firmware is not None else None,
        firmware_update_available=firmware_update_available,
        serial=str(serial) if serial is not None else None,
        online=online,
        last_seen=last_seen,
        clients_count=clients_count,
        router_uptime=router_uptime,
        temperature=temperature,
        signal_strength=signal_strength,
        wan_state=str(wan_state_raw) if wan_state_raw is not None else None,
        connection_state=str(connection_state_raw) if connection_state_raw is not None else None,
        connection_type=str(connection_type_raw) if connection_type_raw is not None else None,
        sim_slot=sim_slot,
        latitude=latitude,
        longitude=longitude,
        location_label=location_label,
        raw=merged,
    )
