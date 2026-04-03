"""Contract tests for Teltonika RMS API models."""

from __future__ import annotations

from typing import cast

import pytest
from pydantic import ValidationError

from custom_components.teltonika_rms.models_api import (
    DeviceDetailResponse,
    DeviceListResponse,
    DeviceState,
    DeviceStateResponse,
)


def test_device_list_response_valid() -> None:
    """Test parsing a valid device list response."""
    data = [
        {
            "id": "1",
            "name": "Router 1",
            "serial": "123456",
            "mac": "00:11:22:33:44:55",
            "model": "RUT955",
            "status": "online",
            "extra_field": "ignore me",
        }
    ]
    response = DeviceListResponse.model_validate({"data": data})
    assert len(response.data) == 1
    assert response.data[0].id == "1"
    assert response.data[0].model_name == "RUT955"


def test_device_list_response_invalid() -> None:
    """Test that missing required fields raise ValidationError."""
    data = [{"name": "Missing ID"}]
    with pytest.raises(ValidationError):
        DeviceListResponse.model_validate({"data": data})


def test_device_detail_response_valid() -> None:
    """Test parsing a valid device detail response."""
    data = {
        "id": "1",
        "serial": "123456",
        "mac": "AA:BB:CC:DD:EE:FF",
        "model": "RUT240",
    }
    response = DeviceDetailResponse.model_validate({"data": data})
    assert response.data.id == "1"
    assert response.data.serial == "123456"


def test_device_state_response_valid() -> None:
    """Test parsing a valid device state response."""
    data = {
        "id": "1",
        "online": True,
        "wan_ip": "1.2.3.4",
    }
    response = DeviceStateResponse.model_validate({"data": data})
    state = cast(DeviceState, response.data)
    assert state.id == "1"
