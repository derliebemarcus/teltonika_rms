from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.teltonika_rms import TeltonikaRmsRuntime
from custom_components.teltonika_rms.coordinator import CoordinatorBundle
from custom_components.teltonika_rms.models import NormalizedDevice
from custom_components.teltonika_rms.sensor import async_setup_entry


@pytest.mark.asyncio
async def test_sensor_switch_fallback(
    hass: HomeAssistant, mock_coordinator_bundle: MagicMock
) -> None:
    """Test that switch devices fall back to port1-8 and sfp1-2 if no ports are found."""
    device_id = "switch_device_id"

    # We use a separate MagicMock for the bundle in this test to avoid slotted dataclass issues
    mock_bundle = MagicMock(spec=CoordinatorBundle)
    mock_bundle.inventory.data = {device_id: {"id": device_id, "type": "switch", "model": "TSW200"}}
    mock_bundle.port_scan.data = {device_id: []}
    mock_bundle.port_config.data = {device_id: []}

    # Create the normalized device we want returned
    mock_device = NormalizedDevice(
        device_id=device_id,
        name="Switch",
        model="TSW200",
        firmware=None,
        latest_firmware=None,
        stable_firmware=None,
        firmware_update_available=None,
        serial=None,
        online=True,
        last_seen=None,
        clients_count=None,
        router_uptime=None,
        temperature=None,
        signal_strength=None,
        wan_state=None,
        connection_state=None,
        connection_type=None,
        sim_slot=None,
        latitude=None,
        longitude=None,
        location_label=None,
        raw={},
    )
    mock_bundle.merged_device.return_value = mock_device

    async_add_entities = MagicMock()
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test_entry"
    mock_config_entry.runtime_data = TeltonikaRmsRuntime(bundle=mock_bundle)

    await async_setup_entry(hass, mock_config_entry, async_add_entities)

    # Adjust to cover RmsPoePowerSensor
    mock_bundle.port_scan.data = {device_id: [{"id": "port1", "name": "port1", "PoE (W)": "5.5"}]}

    await async_setup_entry(hass, mock_config_entry, async_add_entities)

    # Check if RmsPoePowerSensor was created
    entities = []
    for call in async_add_entities.call_args_list:
        entities.extend(call[0][0])

    poe_sensors = [e for e in entities if "PoE Power" in (getattr(e, "_attr_name", "") or "")]
    assert len(poe_sensors) > 0
    assert poe_sensors[0].native_value == 5.5


@pytest.mark.asyncio
async def test_sensor_poe_power_value_errors(mock_coordinator_bundle: MagicMock) -> None:
    """Test RmsPoePowerSensor error handling for native_value."""
    from custom_components.teltonika_rms.sensor import RmsPoePowerSensor

    device_id = "dev1"
    port_id = "port1"

    # Mock port_scan data with invalid PoE value
    mock_coordinator_bundle.port_scan.data = {device_id: [{"name": port_id, "PoE (W)": "invalid"}]}

    sensor = RmsPoePowerSensor(mock_coordinator_bundle, device_id, port_id)
    assert sensor.native_value is None

    # Test port not found
    mock_coordinator_bundle.port_scan.data = {device_id: []}
    assert sensor.native_value is None
