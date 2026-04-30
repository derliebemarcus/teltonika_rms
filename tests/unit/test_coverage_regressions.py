from custom_components.teltonika_rms.api import _extract_grouped_payload, _find_data_in_events
from custom_components.teltonika_rms.sensor import _apply_scan_results, _get_initial_ports


def test_api_find_data_in_events() -> None:
    # 1. Valid structure
    events = [{"data": [{"data": [{"id": "row1"}]}]}]
    assert _find_data_in_events(events) == [{"id": "row1"}]

    # 2. Invalid event type
    assert _find_data_in_events([None, "string"]) is None

    # 3. Missing 'data' field
    assert _find_data_in_events([{}]) is None

    # 4. 'data' field not a list
    assert _find_data_in_events([{"data": "not_a_list"}]) is None

    # 5. Inner item not a dict or missing inner 'data'
    assert _find_data_in_events([{"data": [None, {"no_data": 1}]}]) is None


def test_api_extract_grouped_payload_edge_cases() -> None:
    # 1. Empty payload
    assert _extract_grouped_payload({}) is None

    # 2. Key with invalid data
    assert _extract_grouped_payload({"key": "not_a_list"}) is None

    # 3. Key with empty list
    assert _extract_grouped_payload({"key": []}) is None

    # 4. Success case (through _find_data_in_events)
    payload = {"k": [{"data": [{"data": [{"id": "x"}]}]}]}
    assert _extract_grouped_payload(payload) == [{"id": "x"}]


def test_sensor_get_initial_ports() -> None:
    from unittest.mock import MagicMock

    bundle = MagicMock()
    # 1. With config data
    bundle.port_config.data = {"dev1": [{"id": "p1"}]}
    ports = _get_initial_ports(bundle, "dev1", "RUTX11")
    assert "p1" in ports

    # 2. Switch model with no config
    bundle.port_config.data = {"dev1": []}
    ports = _get_initial_ports(bundle, "dev1", "TSW200")
    assert "port1" in ports
    assert "sfp1" in ports


def test_sensor_apply_scan_results() -> None:
    from unittest.mock import MagicMock

    bundle = MagicMock()
    bundle.port_scan.data = {
        "dev1": [
            {"name": "NIL"},
            {"name": "port1", "status": "up"},
            {"name": "port2", "status": "down"},
        ]
    }
    ports = {"port1": {"id": "port1", "old": True}}
    _apply_scan_results(bundle, "dev1", ports)
    assert ports["port1"]["status"] == "up"
    assert ports["port1"]["old"] is True
    assert "port2" in ports
