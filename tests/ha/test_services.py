"""High-value runtime tests for the Teltonika RMS Home Assistant services."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.teltonika_rms import DOMAIN, SERVICE_GET_DEVICE_HISTORY
from custom_components.teltonika_rms.coordinator import CoordinatorBundle

pytestmark = pytest.mark.ha


async def test_get_device_history_service_calls_api_and_fires_event(
    hass: HomeAssistant,
    mock_rms_api_client: AsyncMock,
    mock_coordinator_bundle: CoordinatorBundle,
) -> None:
    """Test that the get_device_history service calls the API and fires an event."""
    mock_rms_api_client.async_get_device_history.return_value = [
        {"timestamp": "2026-01-01T00:00:00Z", "value": 10}
    ]

    # Mock the config entry to provide the runtime_data
    mock_config_entry = AsyncMock()
    mock_config_entry.domain = DOMAIN
    mock_config_entry.runtime_data = mock_coordinator_bundle
    hass.config_entries._entries = [mock_config_entry]

    # Listen for the event
    events = []
    hass.bus.async_listen_once(f"{DOMAIN}_device_history", lambda e: events.append(e))

    await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_DEVICE_HISTORY,
        {
            "device_id": "test-device-id",
            "from_time": datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
            "to_time": datetime(2026, 1, 1, 1, 0, 0, tzinfo=UTC),
            "interval": "1h",
            "config_id": 123,
        },
        blocking=True,
    )

    # Verify API call
    mock_rms_api_client.async_get_device_history.assert_awaited_once_with(
        device_id="test-device-id",
        from_time=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
        to_time=datetime(2026, 1, 1, 1, 0, 0, tzinfo=UTC),
        interval="1h",
        config_id=123,
        keys=None,
    )

    # Verify event fired
    assert len(events) == 1
    event_data = events[0].data
    assert event_data["device_id"] == "test-device-id"
    assert event_data["config_id"] == 123
    assert event_data["data"] == [{"timestamp": "2026-01-01T00:00:00Z", "value": 10}]


async def test_get_device_history_service_handles_keys_param(
    hass: HomeAssistant,
    mock_rms_api_client: AsyncMock,
    mock_coordinator_bundle: CoordinatorBundle,
) -> None:
    """Test that the get_device_history service correctly passes keys to the API."""
    mock_rms_api_client.async_get_device_history.return_value = [
        {"timestamp": "2026-01-01T00:00:00Z", "temp": 25}
    ]

    mock_config_entry = AsyncMock()
    mock_config_entry.domain = DOMAIN
    mock_config_entry.runtime_data = mock_coordinator_bundle
    hass.config_entries._entries = [mock_config_entry]

    events = []
    hass.bus.async_listen_once(f"{DOMAIN}_device_history", lambda e: events.append(e))

    await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_DEVICE_HISTORY,
        {
            "device_id": "test-device-id-2",
            "from_time": datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
            "to_time": datetime(2026, 1, 1, 1, 0, 0, tzinfo=UTC),
            "interval": "1h",
            "keys": "temperature,humidity",
        },
        blocking=True,
    )

    mock_rms_api_client.async_get_device_history.assert_awaited_once_with(
        device_id="test-device-id-2",
        from_time=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
        to_time=datetime(2026, 1, 1, 1, 0, 0, tzinfo=UTC),
        interval="1h",
        config_id=None,
        keys=["temperature", "humidity"],
    )
    assert len(events) == 1


async def test_get_device_history_service_fires_error_event_on_api_failure(
    hass: HomeAssistant,
    mock_rms_api_client: AsyncMock,
    mock_coordinator_bundle: CoordinatorBundle,
) -> None:
    """Test that the get_device_history service fires an error event on API failure."""
    mock_rms_api_client.async_get_device_history.side_effect = Exception("API down")

    mock_config_entry = AsyncMock()
    mock_config_entry.domain = DOMAIN
    mock_config_entry.runtime_data = mock_coordinator_bundle
    hass.config_entries._entries = [mock_config_entry]

    error_events = []
    hass.bus.async_listen_once(f"{DOMAIN}_device_history_error", lambda e: error_events.append(e))

    await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_DEVICE_HISTORY,
        {
            "device_id": "test-device-id-error",
            "from_time": datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
            "to_time": datetime(2026, 1, 1, 1, 0, 0, tzinfo=UTC),
            "interval": "1h",
            "keys": "temp",
        },
        blocking=True,
    )

    assert len(error_events) == 1
    assert error_events[0].data["device_id"] == "test-device-id-error"
    assert "API down" in error_events[0].data["error"]


async def test_get_device_history_service_invalid_input_no_api_call(
    hass: HomeAssistant,
    mock_rms_api_client: AsyncMock,
    mock_coordinator_bundle: CoordinatorBundle,
) -> None:
    """Test that the service does not call the API with invalid input."""
    mock_config_entry = AsyncMock()
    mock_config_entry.domain = DOMAIN
    mock_config_entry.runtime_data = mock_coordinator_bundle
    hass.config_entries._entries = [mock_config_entry]

    # Missing device_id
    with patch("custom_components.teltonika_rms.__init__.LOGGER.error") as mock_logger_error:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_GET_DEVICE_HISTORY,
            {
                "from_time": datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
                "to_time": datetime(2026, 1, 1, 1, 0, 0, tzinfo=UTC),
                "interval": "1h",
                "keys": "temp",
            },
            blocking=True,
        )
        mock_logger_error.assert_called_once()

    mock_rms_api_client.async_get_device_history.assert_not_awaited()

    # Missing config_id and keys
    mock_rms_api_client.async_get_device_history.reset_mock()
    with patch("custom_components.teltonika_rms.__init__.LOGGER.error") as mock_logger_error:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_GET_DEVICE_HISTORY,
            {
                "device_id": "test-device-id-no-params",
                "from_time": datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
                "to_time": datetime(2026, 1, 1, 1, 0, 0, tzinfo=UTC),
                "interval": "1h",
            },
            blocking=True,
        )
        mock_logger_error.assert_called_once()
    mock_rms_api_client.async_get_device_history.assert_not_awaited()


async def test_unload_removes_history_service(hass: HomeAssistant) -> None:
    """Test that the get_device_history service is removed on unload."""
    # Assume service is registered
    hass.services.async_register(DOMAIN, SERVICE_GET_DEVICE_HISTORY, AsyncMock())

    # Mock _merged_options to avoid dependency issues during unload test
    with patch("custom_components.teltonika_rms.__init__._merged_options", return_value={}):
        result = await hass.config_entries.async_unload_platforms(
            AsyncMock(), []
        )  # Pass an empty list for platforms if you don't care about them
        assert result is True

        # Verify service is removed if no other entries exist
        hass.config_entries._entries = []  # Simulate no other entries
        await hass.config_entries.async_unload_entry(
            AsyncMock(domain=DOMAIN, runtime_data=AsyncMock())
        )
        assert not hass.services.has_service(DOMAIN, SERVICE_GET_DEVICE_HISTORY)


# Existing test_setup_entry_succeeds and test_setup_entry_fails_on_auth should also cover the service registration/deregistration flow generally
