"""Coordinator, entity, diagnostics, and status-channel tests."""

from __future__ import annotations

import asyncio
import tempfile
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from teltonika_rms import TeltonikaRmsRuntime
from teltonika_rms.binary_sensor import RmsOnlineBinarySensor, async_setup_entry as binary_setup
from teltonika_rms.coordinator import (
    CoordinatorBundle,
    InventoryCoordinator,
    StateCoordinator,
    async_refresh_all,
    validate_request_budget,
)
from teltonika_rms.device_tracker import RmsDeviceTracker, async_setup_entry as tracker_setup
from teltonika_rms.diagnostics import TO_REDACT, async_get_config_entry_diagnostics
from teltonika_rms.endpoint_matrix import EndpointMatrix, EndpointSpec
from teltonika_rms.entity import TeltonikaRmsEntity
from teltonika_rms.exceptions import RmsApiError
from teltonika_rms.models import NormalizedDevice
from teltonika_rms.sensor import (
    RmsFirmwareSensor,
    RmsLastSeenSensor,
    RmsModelSensor,
    RmsSerialSensor,
    async_setup_entry as sensor_setup,
)
from teltonika_rms.status_channel import (
    RmsStatusChannelManager,
    _coerce_payload,
    _is_terminal,
)

pytestmark = pytest.mark.ha


class FakeListenerCoordinator:
    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self.data = data or {}
        self.listeners: list[Any] = []
        self.refresh_calls = 0
        self.update_interval = timedelta(seconds=120)

    def async_add_listener(self, callback: Any) -> Any:
        self.listeners.append(callback)
        return lambda: None

    async def async_request_refresh(self) -> None:
        self.refresh_calls += 1


def _normalized(
    *,
    device_id: str = "dev-1",
    online: bool | None = True,
    latitude: float | None = 47.0,
    longitude: float | None = 8.0,
) -> NormalizedDevice:
    return NormalizedDevice(
        device_id=device_id,
        name="Router",
        model="RUTX",
        firmware="1.0",
        serial="SERIAL",
        online=online,
        last_seen=datetime(2026, 3, 13, 12, 0, tzinfo=UTC),
        latitude=latitude,
        longitude=longitude,
        location_label="Zurich",
        raw={"id": device_id},
    )


def _bundle(normalized: NormalizedDevice | None) -> Any:
    inventory = FakeListenerCoordinator({"dev-1": {"id": "dev-1"}})
    state = FakeListenerCoordinator({"dev-1": {"state": {"online": True}}})
    return SimpleNamespace(
        inventory=inventory,
        state=state,
        merged_device=lambda device_id: normalized if device_id == "dev-1" else None,
    )


def _matrix(aggregate: bool = True) -> EndpointMatrix:
    endpoints = {
        "devices_list": EndpointSpec("/v3/devices", tuple(), "safe"),
        "device_detail": EndpointSpec("/v3/devices/{id}", tuple(), "safe"),
        "device_state_single": EndpointSpec("/v3/devices/{id}/status", tuple(), "async-channel"),
        "device_location": EndpointSpec("/v3/devices/{id}/location", tuple(), "high-cost"),
    }
    if aggregate:
        endpoints["device_state_aggregate"] = EndpointSpec("/v3/devices/status", tuple(), "async-channel")
    return EndpointMatrix(source="test", endpoints=endpoints)


def test_base_entity_and_platform_entities_expose_values() -> None:
    bundle = _bundle(_normalized())

    base = TeltonikaRmsEntity(bundle, "dev-1")
    binary = RmsOnlineBinarySensor(bundle, "dev-1")
    model = RmsModelSensor(bundle, "dev-1")
    firmware = RmsFirmwareSensor(bundle, "dev-1")
    serial = RmsSerialSensor(bundle, "dev-1")
    last_seen = RmsLastSeenSensor(bundle, "dev-1")
    tracker = RmsDeviceTracker(bundle, "dev-1")

    assert base.available is True
    assert base.device_info is not None
    assert binary.is_on is True
    assert model.native_value == "RUTX"
    assert firmware.native_value == "1.0"
    assert serial.native_value == "SERIAL"
    assert last_seen.native_value is not None
    assert tracker.available is True
    assert tracker.latitude == 47.0
    assert tracker.longitude == 8.0
    assert tracker.extra_state_attributes["location_detail"] == "Zurich"
    assert tracker.location_accuracy == 100


def test_tracker_and_base_entity_handle_missing_location() -> None:
    bundle = _bundle(_normalized(latitude=None, longitude=None))

    tracker = RmsDeviceTracker(bundle, "dev-1")
    base = TeltonikaRmsEntity(bundle, "missing")

    assert tracker.available is False
    assert tracker.extra_state_attributes == {"location_detail": "Zurich"}
    assert base.available is False
    assert base.device_info is None


def test_platform_setup_entry_adds_expected_entities() -> None:
    bundle = _bundle(_normalized())
    runtime = TeltonikaRmsRuntime(bundle=bundle)
    entry = SimpleNamespace(runtime_data=runtime, async_on_unload=lambda cb: None)
    added_binary: list[Any] = []
    added_sensor: list[Any] = []
    added_tracker: list[Any] = []

    asyncio.run(binary_setup(None, entry, added_binary.extend))
    asyncio.run(sensor_setup(None, entry, added_sensor.extend))
    asyncio.run(tracker_setup(None, entry, added_tracker.extend))

    assert len(added_binary) == 1
    assert len(added_sensor) == 4
    assert len(added_tracker) == 1


def test_coordinator_bundle_and_budget_validation() -> None:
    inventory = FakeListenerCoordinator({"dev-1": {"id": "dev-1", "name": "Router"}})
    state = FakeListenerCoordinator({"dev-1": {"state": {"online": True}, "location": {"latitude": 1, "longitude": 2}}})
    bundle = CoordinatorBundle(
        inventory=inventory,  # type: ignore[arg-type]
        state=state,  # type: ignore[arg-type]
        status_channels=SimpleNamespace(),
        api=SimpleNamespace(),
    )

    merged = bundle.merged_device("dev-1")

    assert merged is not None
    assert merged.online is True
    assert validate_request_budget(
        inventory_interval=900,
        state_interval=120,
        estimated_devices=10,
        aggregate_state_supported=True,
    ) is True


def test_inventory_and_state_coordinator_update_methods(monkeypatch: pytest.MonkeyPatch) -> None:
    inventory = object.__new__(InventoryCoordinator)
    inventory._api = SimpleNamespace(
        async_list_devices=lambda **kwargs: asyncio.sleep(0, result=[{"id": "dev-1", "name": "Router"}])
    )
    inventory._tags = ["alpha"]
    inventory._device_status = None

    updated = asyncio.run(inventory._async_update_data())
    assert updated == {"dev-1": {"id": "dev-1", "name": "Router"}}

    failing_inventory = object.__new__(InventoryCoordinator)
    failing_inventory._api = SimpleNamespace(async_list_devices=lambda **kwargs: asyncio.sleep(0, result=None))
    failing_inventory._tags = []
    failing_inventory._device_status = None

    async def _raise_list(**kwargs: Any) -> Any:
        raise RmsApiError("bad inventory")

    failing_inventory._api.async_list_devices = _raise_list
    with pytest.raises(UpdateFailed):
        asyncio.run(failing_inventory._async_update_data())

    state = object.__new__(StateCoordinator)
    state._api = SimpleNamespace(
        endpoint_matrix=_matrix(aggregate=False),
        async_get_states_for_devices=lambda device_ids, max_per_cycle: asyncio.sleep(
            0, result={"dev-1": {"online": True}}
        ),
        async_get_device_location=lambda device_id: asyncio.sleep(0, result={"latitude": 1.0, "longitude": 2.0}),
        estimate_max_calls_per_cycle=lambda interval: 3,
    )
    state._inventory = SimpleNamespace(data={"dev-1": {"id": "dev-1"}}, update_interval=timedelta(seconds=900))
    state._enable_location = True
    state._estimated_devices = 10
    state._state_interval = 120

    result = asyncio.run(state._async_update_data())

    assert result["dev-1"]["state"] == {"online": True}
    assert result["dev-1"]["location"] == {"latitude": 1.0, "longitude": 2.0}
    assert state.monthly_request_estimate > 0

    async def _raise_state(device_ids: list[str], max_per_cycle: int | None) -> Any:
        raise RmsApiError("bad state")

    state._api.async_get_states_for_devices = _raise_state
    with pytest.raises(UpdateFailed):
        asyncio.run(state._async_update_data())


def test_coordinator_handles_auth_failed_and_refresh_all() -> None:
    inventory = object.__new__(InventoryCoordinator)

    async def _auth_fail(**kwargs: Any) -> Any:
        raise ConfigEntryAuthFailed("denied")

    inventory._api = SimpleNamespace(async_list_devices=_auth_fail)
    inventory._tags = []
    inventory._device_status = None
    with pytest.raises(ConfigEntryAuthFailed):
        asyncio.run(inventory._async_update_data())

    bundle = SimpleNamespace(inventory=FakeListenerCoordinator(), state=FakeListenerCoordinator())
    asyncio.run(async_refresh_all(bundle))
    assert bundle.inventory.refresh_calls == 1
    assert bundle.state.refresh_calls == 1


def test_diagnostics_redacts_sensitive_fields() -> None:
    bundle = SimpleNamespace(
        api=SimpleNamespace(request_counter=7, endpoint_matrix=_matrix()),
        inventory=SimpleNamespace(data={"a": {}}),
        state=SimpleNamespace(data={"a": {}}),
    )
    entry = SimpleNamespace(
        entry_id="entry-1",
        title="Teltonika RMS",
        data={"access_token": "secret", "pat_token": "secret", "other": "keep"},
        options={"interval": 60},
        runtime_data=TeltonikaRmsRuntime(bundle=bundle),
    )

    diagnostics = asyncio.run(async_get_config_entry_diagnostics(None, entry))

    assert diagnostics["entry"]["data"]["other"] == "keep"
    for key in TO_REDACT:
        if key in diagnostics["entry"]["data"]:
            assert diagnostics["entry"]["data"][key] == "**REDACTED**"
    assert diagnostics["runtime"]["request_counter"] == 7


def test_status_channel_manager_and_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = RmsStatusChannelManager(SimpleNamespace())

    async def _socket(channel_id: str, timeout_seconds: int) -> dict[str, Any] | None:
        return {"completed": True}

    async def _poll(channel_id: str, timeout_seconds: int) -> dict[str, Any] | None:
        return {"completed": True}

    monkeypatch.setattr(manager, "_async_wait_via_socket", _socket)
    monkeypatch.setattr(manager, "_async_wait_via_polling", _poll)
    assert asyncio.run(manager.async_wait_for_channel("abc")) == {"completed": True}
    assert asyncio.run(manager.async_wait_for_channel("")) is None

    async def _done_payload(channel_id: str) -> dict[str, Any]:
        return {"status": "done"}

    async def _no_token() -> None:
        return None

    polling_api = SimpleNamespace(
        async_poll_status_channel=_done_payload,
        async_get_access_token=_no_token,
    )
    polling_manager = RmsStatusChannelManager(polling_api)

    async def _sleep(delay: float) -> None:
        return None

    monkeypatch.setattr("teltonika_rms.status_channel.asyncio.sleep", _sleep)
    assert asyncio.run(polling_manager._async_wait_via_polling("abc", 2)) == {"status": "done"}
    assert asyncio.run(polling_manager._async_wait_via_socket("abc", 1)) is None

    assert _coerce_payload({"ok": True}) == {"ok": True}
    assert _coerce_payload("bad") is None
    assert _is_terminal({"completed": True}) is True
    assert _is_terminal({"status": "success"}) is True
    assert _is_terminal({"status": "pending"}) is False


def test_homeassistant_can_be_constructed_for_coordinator_compatibility() -> None:
    async def _build() -> str:
        with tempfile.TemporaryDirectory() as tmpdir:
            hass = HomeAssistant(tmpdir)
            return hass.config.config_dir

    assert asyncio.run(_build())
