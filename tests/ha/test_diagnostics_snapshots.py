"""Tests for Teltonika RMS diagnostics."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant
from syrupy.assertion import SnapshotAssertion

from custom_components.teltonika_rms import TeltonikaRmsRuntime
from custom_components.teltonika_rms.coordinator import CoordinatorBundle
from custom_components.teltonika_rms.diagnostics import async_get_config_entry_diagnostics


@pytest.mark.asyncio
async def test_async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
) -> None:
    """Test that diagnostics are correctly redacted and structured."""
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test-entry-id"
    mock_config_entry.title = "Test Entry"
    mock_config_entry.data = {
        "access_token": "secret-token",
        "pat_token": "secret-pat",
        "auth_mode": "pat",
    }
    mock_config_entry.options = {"test_option": True}

    mock_bundle = MagicMock(spec=CoordinatorBundle)
    mock_bundle.api.request_counter = 42
    mock_bundle.inventory.data = {"dev1": {}, "dev2": {}}
    mock_bundle.state.data = {"dev1": {}}
    mock_bundle.api._aggregate_state_available = True
    mock_bundle.state.monthly_request_estimate = 100
    mock_bundle.api.endpoint_matrix.source = "test-source"

    mock_spec = MagicMock()
    mock_spec.path = "/test/path"
    mock_bundle.api.endpoint_matrix.endpoints = {"test_endpoint": mock_spec}

    mock_runtime = TeltonikaRmsRuntime(bundle=mock_bundle)
    mock_config_entry.runtime_data = mock_runtime

    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert diagnostics == snapshot
