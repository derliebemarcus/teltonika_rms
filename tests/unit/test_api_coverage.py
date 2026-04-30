from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.teltonika_rms.api import RmsApiClient


def mock_response(status: int = 200, json_data: Any = None, text_data: str = "") -> MagicMock:
    mock = MagicMock()
    mock.status = status
    mock.json = AsyncMock(
        return_value=json_data if json_data is not None else {"success": True, "data": []}
    )
    mock.text = AsyncMock(return_value=text_data)
    mock.release = MagicMock()
    return mock


@pytest.fixture
def mock_auth() -> MagicMock:
    auth = MagicMock()
    auth.async_get_access_token = AsyncMock(return_value="test_token")
    auth.async_request = AsyncMock()
    return auth


@pytest.fixture
def mock_endpoint_matrix() -> MagicMock:
    matrix = MagicMock()
    matrix.path_for.return_value = "/api/test"
    matrix.format_path.return_value = "/api/test/1"
    return matrix


@pytest.fixture
def api(mock_auth: MagicMock, mock_endpoint_matrix: MagicMock) -> RmsApiClient:
    return RmsApiClient(mock_auth, mock_endpoint_matrix)


@pytest.mark.asyncio
async def test_api_async_validate_connection_success(
    api: RmsApiClient, mock_auth: MagicMock
) -> None:
    """Test successful connection validation."""
    mock_auth.async_request.return_value = mock_response(
        json_data={
            "success": True,
            "data": [{"id": 1}],
            "meta": {"pagination": {"page": 1, "pages": 1}},
        }
    )
    await api.async_validate_connection()
    assert mock_auth.async_request.called


@pytest.mark.asyncio
async def test_api_async_list_devices(api: RmsApiClient, mock_auth: MagicMock) -> None:
    """Test getting devices list."""
    mock_auth.async_request.return_value = mock_response(
        json_data={
            "success": True,
            "data": [{"id": 1, "name": "dev1"}],
            "meta": {"pagination": {"page": 1, "pages": 1}},
        }
    )
    result = await api.async_list_devices()
    assert result == [{"id": 1, "name": "dev1"}]


@pytest.mark.asyncio
async def test_api_async_get_device_state(api: RmsApiClient, mock_auth: MagicMock) -> None:
    """Test getting device state."""
    mock_auth.async_request.return_value = mock_response(
        json_data={"success": True, "data": {"online": True}}
    )
    result = await api.async_get_device_state("dev1")
    assert result == {"online": True}


@pytest.mark.asyncio
async def test_api_async_get_device_ethernet_ports(api: RmsApiClient, mock_auth: MagicMock) -> None:
    """Test getting ethernet ports."""
    mock_auth.async_request.return_value = mock_response(json_data={"success": True, "data": []})
    result = await api.async_get_device_ethernet_ports("dev1")
    assert result == []


@pytest.mark.asyncio
async def test_api_async_get_device_port_configurations(
    api: RmsApiClient, mock_auth: MagicMock
) -> None:
    """Test getting port config."""
    mock_auth.async_request.return_value = mock_response(json_data={"success": True, "data": []})
    result = await api.async_get_device_port_configurations("dev1")
    assert result == []


@pytest.mark.asyncio
async def test_api_async_set_device_port_poe(api: RmsApiClient, mock_auth: MagicMock) -> None:
    """Test setting port PoE."""
    mock_auth.async_request.return_value = mock_response(
        json_data={"success": True, "data": {"status": "success"}}
    )
    result = await api.async_set_device_port_poe("dev1", "port1", True)
    assert result == {"status": "success"}


@pytest.mark.asyncio
async def test_api_async_reboot_device(api: RmsApiClient, mock_auth: MagicMock) -> None:
    """Test rebooting device."""
    mock_auth.async_request.return_value = mock_response(
        json_data={"success": True, "data": {"status": "rebooting"}}
    )
    result = await api.async_reboot_device("dev1")
    assert result == {"status": "rebooting"}
