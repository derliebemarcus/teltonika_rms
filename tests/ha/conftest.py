"""Home Assistant specific pytest fixtures for Teltonika RMS tests."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.teltonika_rms.api import RmsApiClient
from custom_components.teltonika_rms.coordinator import CoordinatorBundle


@pytest.fixture
def hass() -> Generator[HomeAssistant, None, None]:
    """Mock HomeAssistant fixture."""
    _hass = AsyncMock(spec=HomeAssistant)
    _hass.config_entries._entries = []
    _hass.services.has_service.return_value = False
    with patch(
        "custom_components.teltonika_rms.PLATFORMS",
        ["binary_sensor", "sensor", "device_tracker"],
    ):
        yield _hass


@pytest.fixture
def mock_rms_api_client() -> Generator[AsyncMock, None, None]:
    """Mock RmsApiClient fixture."""
    with patch(
        "custom_components.teltonika_rms.api.RmsApiClient", autospec=True
    ) as mock_api_client:
        yield mock_api_client.return_value


@pytest.fixture
def mock_coordinator_bundle(
    mock_rms_api_client: AsyncMock,
) -> Generator[CoordinatorBundle, None, None]:
    """Mock CoordinatorBundle fixture."""
    with (
        patch("custom_components.teltonika_rms.coordinator.InventoryCoordinator", autospec=True) as mock_inventory_coordinator,
        patch("custom_components.teltonika_rms.coordinator.StateCoordinator", autospec=True) as mock_state_coordinator,
        patch("custom_components.teltonika_rms.coordinator.PortScanCoordinator", autospec=True) as mock_port_scan_coordinator,
        patch("custom_components.teltonika_rms.coordinator.PortConfigCoordinator", autospec=True) as mock_port_config_coordinator,
        patch("custom_components.teltonika_rms.status_channel.RmsStatusChannelManager", autospec=True) as mock_status_channel_manager,
    ):

        bundle = CoordinatorBundle(
            inventory=mock_inventory_coordinator.return_value,
            state=mock_state_coordinator.return_value,
            port_scan=mock_port_scan_coordinator.return_value,
            port_config=mock_port_config_coordinator.return_value,
            status_channels=mock_status_channel_manager.return_value,
            api=mock_rms_api_client,
        )
        yield bundle
