import pytest

from custom_components.teltonika_rms.api import (
    _coerce_list,
    _coerce_state_map,
    _validate_contract_payload,
)
from custom_components.teltonika_rms.exceptions import RmsApiError
from custom_components.teltonika_rms.models_api import DeviceDetailResponse


def test_validate_contract_payload_error() -> None:
    """Test that ValidationError raises RmsApiError."""
    # Missing required 'data' or malformed
    invalid_payload = {"something": "else"}
    with pytest.raises(RmsApiError, match="RMS schema changed"):
        _validate_contract_payload(invalid_payload, "test_endpoint", DeviceDetailResponse)


def test_coerce_list_edge_cases() -> None:
    """Test _coerce_list with non-standard inputs."""
    assert _coerce_list(None) == []
    assert _coerce_list("not a list") == []

    # Dict with no matching keys
    assert _coerce_list({"unknown": [1, 2]}) == []

    # Dict with matching key but not a list
    assert _coerce_list({"items": "not a list"}) == []


def test_coerce_state_map_nested_devices() -> None:
    """Test _coerce_state_map with nested devices key."""
    data = {"devices": [{"id": "dev1", "status": "online"}, {"id": "dev2", "status": "offline"}]}
    result = _coerce_state_map(data)
    assert "dev1" in result
    assert "dev2" in result
    assert result["dev1"]["status"] == "online"


def test_coerce_state_map_missing_id() -> None:
    """Test _coerce_state_map skips items without ID."""
    data = [{"id": "dev1"}, {"no_id": "here"}, {"device_id": "dev2"}]
    result = _coerce_state_map(data)
    assert "dev1" in result
    assert "dev2" in result
    assert len(result) == 2
