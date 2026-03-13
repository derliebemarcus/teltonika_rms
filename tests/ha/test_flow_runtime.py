"""Config-flow and setup coverage tests."""

from __future__ import annotations

import asyncio
import base64
import json
import importlib
import tempfile
from datetime import timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from teltonika_rms.config_flow import (
    OAuth2FlowHandler,
    TeltonikaRmsOptionsFlow,
    _extract_subject_from_token,
    _token_fingerprint,
)
from teltonika_rms.const import (
    AUTH_MODE_OAUTH2,
    AUTH_MODE_PAT,
    CONF_AUTH_MODE,
    CONF_ENABLE_LOCATION,
    CONF_ESTIMATED_DEVICES,
    CONF_INVENTORY_INTERVAL,
    CONF_PAT_TOKEN,
    CONF_SPEC_PATH,
    CONF_STATE_INTERVAL,
    CONF_TAGS,
    DEFAULT_OPTIONS,
    OAUTH2_SCOPES,
)
from teltonika_rms.endpoint_matrix import EndpointMatrix, EndpointSpec

pytestmark = pytest.mark.ha

integration = importlib.import_module("teltonika_rms")


def _make_token(payload: dict[str, Any]) -> str:
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8").rstrip("=")
    return f"header.{encoded}.signature"


class FakeFlowHass:
    def __init__(self) -> None:
        self._entry = None
        self.config_entries = SimpleNamespace(async_get_entry=lambda entry_id: self._entry)


class FakeServices:
    def __init__(self) -> None:
        self.registered: dict[tuple[str, str], Any] = {}
        self.removed: list[tuple[str, str]] = []

    def has_service(self, domain: str, service: str) -> bool:
        return (domain, service) in self.registered

    def async_register(self, domain: str, service: str, handler: Any) -> None:
        self.registered[(domain, service)] = handler

    def async_remove(self, domain: str, service: str) -> None:
        self.removed.append((domain, service))


class FakeConfigEntries:
    def __init__(self) -> None:
        self.forwarded: list[tuple[Any, tuple[str, ...]]] = []
        self.reloaded: list[str] = []
        self.entries_result: list[Any] = []

    async def async_forward_entry_setups(self, entry: Any, platforms: tuple[str, ...]) -> None:
        self.forwarded.append((entry, platforms))

    async def async_unload_platforms(self, entry: Any, platforms: tuple[str, ...]) -> bool:
        return True

    def async_entries(self, domain: str) -> list[Any]:
        return list(self.entries_result)

    async def async_reload(self, entry_id: str) -> None:
        self.reloaded.append(entry_id)


class FakeHass:
    def __init__(self) -> None:
        self.services = FakeServices()
        self.config_entries = FakeConfigEntries()

    async def async_add_executor_job(self, func: Any, *args: Any) -> Any:
        return func(*args)


def _test_matrix(aggregate: bool = True) -> EndpointMatrix:
    endpoints = {
        "devices_list": EndpointSpec("/v3/devices", tuple(), "safe"),
        "device_detail": EndpointSpec("/v3/devices/{id}", tuple(), "safe"),
        "device_state_single": EndpointSpec("/v3/devices/{id}/status", tuple(), "async-channel"),
        "device_location": EndpointSpec("/v3/devices/{id}/location", tuple(), "high-cost"),
    }
    if aggregate:
        endpoints["device_state_aggregate"] = EndpointSpec("/v3/devices/status", tuple(), "async-channel")
    return EndpointMatrix(source="test", endpoints=endpoints)


def test_flow_extra_authorize_data_contains_scopes() -> None:
    flow = OAuth2FlowHandler()
    assert flow.extra_authorize_data == {"scope": " ".join(OAUTH2_SCOPES)}
    assert flow.logger.name.endswith("config_flow")


def test_user_and_oauth2_steps_delegate_to_homeassistant_base(monkeypatch: pytest.MonkeyPatch) -> None:
    flow = OAuth2FlowHandler()
    flow.async_show_menu = lambda **kwargs: kwargs  # type: ignore[method-assign]
    result = asyncio.run(flow.async_step_user())
    assert result == {"step_id": "user", "menu_options": ["oauth2", "pat"]}

    async def _base_user(self: Any, user_input: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"type": "external", "user_input": user_input}

    monkeypatch.setattr(
        "homeassistant.helpers.config_entry_oauth2_flow.AbstractOAuth2FlowHandler.async_step_user",
        _base_user,
    )
    assert asyncio.run(flow.async_step_oauth2({"x": 1})) == {"type": "external", "user_input": {"x": 1}}


def test_pat_step_rejects_empty_token() -> None:
    flow = OAuth2FlowHandler()
    flow.async_show_form = lambda **kwargs: kwargs  # type: ignore[method-assign]

    result = asyncio.run(flow.async_step_pat({CONF_PAT_TOKEN: "   "}))

    assert result["errors"]["base"] == "invalid_pat"


def test_reauth_pat_rejects_empty_token_and_missing_entry() -> None:
    flow = OAuth2FlowHandler()
    flow.async_show_form = lambda **kwargs: kwargs  # type: ignore[method-assign]
    flow.async_abort = lambda **kwargs: kwargs  # type: ignore[method-assign]

    empty = asyncio.run(flow.async_step_reauth_pat({CONF_PAT_TOKEN: "   "}))
    assert empty["errors"]["base"] == "invalid_pat"

    missing = asyncio.run(flow.async_step_reauth_pat({CONF_PAT_TOKEN: "token"}))
    assert missing["reason"] == "reauth_failed"


def test_pat_step_creates_entry_for_valid_token() -> None:
    flow = OAuth2FlowHandler()
    seen: dict[str, Any] = {}

    async def _set_unique_id(unique_id: str) -> None:
        seen["unique_id"] = unique_id

    flow.async_set_unique_id = _set_unique_id  # type: ignore[method-assign]
    flow._abort_if_unique_id_configured = lambda: seen.setdefault("abort_checked", True)  # type: ignore[method-assign]
    flow.async_create_entry = lambda **kwargs: kwargs  # type: ignore[method-assign]

    result = asyncio.run(flow.async_step_pat({CONF_PAT_TOKEN: "pat-123"}))

    assert result["data"][CONF_AUTH_MODE] == AUTH_MODE_PAT
    assert result["data"][CONF_PAT_TOKEN] == "pat-123"
    assert seen["unique_id"].startswith("pat_")
    assert result["options"] == dict(DEFAULT_OPTIONS)


def test_reauth_step_handles_missing_entry() -> None:
    flow = OAuth2FlowHandler()
    flow.hass = FakeFlowHass()  # type: ignore[assignment]
    flow.context = {"entry_id": "missing"}
    flow.async_abort = lambda **kwargs: kwargs  # type: ignore[method-assign]

    result = asyncio.run(flow.async_step_reauth({}))

    assert result["reason"] == "reauth_failed"


def test_reauth_step_routes_by_existing_auth_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    flow = OAuth2FlowHandler()
    pat_entry = SimpleNamespace(data={CONF_AUTH_MODE: AUTH_MODE_PAT})
    flow.hass = FakeFlowHass()  # type: ignore[assignment]
    flow.hass._entry = pat_entry
    flow.context = {"entry_id": "entry-1"}

    async def _reauth_pat() -> dict[str, str]:
        return {"step": "pat"}

    flow.async_step_reauth_pat = _reauth_pat  # type: ignore[method-assign]
    assert asyncio.run(flow.async_step_reauth({})) == {"step": "pat"}

    async def _pick_impl(user_input: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"step": "oauth", "entry_data": user_input}

    flow.async_step_pick_implementation = _pick_impl  # type: ignore[method-assign]
    flow.hass._entry = SimpleNamespace(data={CONF_AUTH_MODE: AUTH_MODE_OAUTH2})
    assert asyncio.run(flow.async_step_reauth({"x": 1})) == {"step": "oauth", "entry_data": None}


def test_reauth_pat_updates_token() -> None:
    flow = OAuth2FlowHandler()
    flow._reauth_entry = SimpleNamespace(unique_id="x")
    flow.async_update_reload_and_abort = lambda entry, data_updates: {"entry": entry, "data": data_updates}  # type: ignore[method-assign]

    result = asyncio.run(flow.async_step_reauth_pat({CONF_PAT_TOKEN: "new-token"}))

    assert result["data"][CONF_PAT_TOKEN] == "new-token"
    assert result["data"][CONF_AUTH_MODE] == AUTH_MODE_PAT


def test_oauth_create_entry_and_reauth_paths() -> None:
    token = {"token": {"access_token": _make_token({"sub": "user-1"})}}

    flow = OAuth2FlowHandler()
    flow.context = {"source": "user"}
    seen: dict[str, Any] = {}

    async def _set_unique_id(unique_id: str) -> None:
        seen["unique_id"] = unique_id

    flow.async_set_unique_id = _set_unique_id  # type: ignore[method-assign]
    flow._abort_if_unique_id_configured = lambda: seen.setdefault("abort_checked", True)  # type: ignore[method-assign]
    flow.async_create_entry = lambda **kwargs: kwargs  # type: ignore[method-assign]

    created = asyncio.run(flow.async_oauth_create_entry(token))
    assert created["data"][CONF_AUTH_MODE] == AUTH_MODE_OAUTH2
    assert seen["unique_id"] == "user-1"

    reauth_flow = OAuth2FlowHandler()
    reauth_flow.context = {"source": "reauth"}
    reauth_flow._reauth_entry = SimpleNamespace(unique_id="different")
    reauth_flow.async_set_unique_id = _set_unique_id  # type: ignore[method-assign]
    reauth_flow.async_abort = lambda **kwargs: kwargs  # type: ignore[method-assign]

    aborted = asyncio.run(reauth_flow.async_oauth_create_entry(token))
    assert aborted["reason"] == "wrong_account"


def test_oauth_reauth_updates_matching_entry_and_exposes_options_flow() -> None:
    token = {"token": {"access_token": _make_token({"sub": "user-1"})}}
    flow = OAuth2FlowHandler()
    flow.context = {"source": "reauth"}
    flow._reauth_entry = SimpleNamespace(unique_id="user-1")
    flow.async_set_unique_id = lambda unique_id: asyncio.sleep(0)  # type: ignore[method-assign]
    flow.async_update_reload_and_abort = lambda entry, data_updates: {  # type: ignore[method-assign]
        "entry": entry,
        "data": data_updates,
    }

    result = asyncio.run(flow.async_oauth_create_entry(token))

    assert result["data"][CONF_AUTH_MODE] == AUTH_MODE_OAUTH2
    assert isinstance(OAuth2FlowHandler.async_get_options_flow(SimpleNamespace()), TeltonikaRmsOptionsFlow)


def test_options_flow_handles_budget_and_normalizes_tags(monkeypatch: pytest.MonkeyPatch) -> None:
    flow = TeltonikaRmsOptionsFlow(SimpleNamespace(options={}))
    flow.hass = FakeHass()  # type: ignore[assignment]
    flow.async_create_entry = lambda **kwargs: kwargs  # type: ignore[method-assign]
    flow.async_show_form = lambda **kwargs: kwargs  # type: ignore[method-assign]
    monkeypatch.setattr("teltonika_rms.config_flow.load_endpoint_matrix", lambda path: _test_matrix())

    result = asyncio.run(
        flow.async_step_init(
            {
                CONF_INVENTORY_INTERVAL: 300,
                CONF_STATE_INTERVAL: 120,
                CONF_ESTIMATED_DEVICES: 20,
                CONF_TAGS: " alpha, beta ",
                "device_status": "",
                CONF_SPEC_PATH: "",
                CONF_ENABLE_LOCATION: True,
            }
        )
    )

    assert result["data"][CONF_TAGS] == "alpha,beta"

    monkeypatch.setattr(
        "teltonika_rms.config_flow.load_endpoint_matrix",
        lambda path: _test_matrix(aggregate=False),
    )
    excessive = asyncio.run(
        flow.async_step_init(
            {
                CONF_INVENTORY_INTERVAL: 60,
                CONF_STATE_INTERVAL: 60,
                CONF_ESTIMATED_DEVICES: 500,
                CONF_TAGS: "",
                "device_status": "",
                CONF_SPEC_PATH: "",
                CONF_ENABLE_LOCATION: True,
            }
        )
    )
    assert excessive["errors"]["base"] == "request_budget_exceeded"


def test_options_flow_shows_defaults_when_opened_without_input() -> None:
    flow = TeltonikaRmsOptionsFlow(SimpleNamespace(options={CONF_STATE_INTERVAL: 240}))
    flow.async_show_form = lambda **kwargs: kwargs  # type: ignore[method-assign]

    result = asyncio.run(flow.async_step_init())

    assert result["step_id"] == "init"
    assert result["errors"] == {}


def test_token_helpers_extract_subject_and_fingerprint() -> None:
    token = {"token": {"access_token": _make_token({"sub": "abc"})}}
    assert _extract_subject_from_token(token) == "abc"
    assert _extract_subject_from_token({"token": "bad"}) is None
    assert _extract_subject_from_token({"token": {CONF_ACCESS_TOKEN: 1}}) is None
    assert _extract_subject_from_token({"token": {"access_token": "broken"}}) is None
    assert _extract_subject_from_token({"token": {"access_token": "x.bad.signature"}}) is None
    assert len(_token_fingerprint("secret")) == 16


def test_integration_merged_options_and_refresh_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    entry = SimpleNamespace(options={CONF_STATE_INTERVAL: 999})
    merged = integration._merged_options(entry)
    assert merged[CONF_STATE_INTERVAL] == 999
    assert merged[CONF_INVENTORY_INTERVAL] == DEFAULT_OPTIONS[CONF_INVENTORY_INTERVAL]

    calls: list[str] = []

    async def _refresh(bundle: Any) -> None:
        calls.append(bundle)

    monkeypatch.setattr("teltonika_rms.coordinator.async_refresh_all", _refresh)

    hass = FakeHass()
    hass.config_entries.entries_result = [
        SimpleNamespace(runtime_data=SimpleNamespace(bundle="bundle-1")),
        SimpleNamespace(runtime_data=None),
    ]
    handler = integration._build_refresh_handler(hass)  # type: ignore[arg-type]
    asyncio.run(handler(None))

    assert calls == ["bundle-1"]


def test_integration_unload_and_reload_entry() -> None:
    hass = FakeHass()
    entry = SimpleNamespace(entry_id="entry-1")
    hass.config_entries.entries_result = []
    hass.services.registered[("teltonika_rms", "refresh")] = object()

    unloaded = asyncio.run(integration.async_unload_entry(hass, entry))
    asyncio.run(integration.async_reload_entry(hass, entry))

    assert unloaded is True
    assert ("teltonika_rms", "refresh") in hass.services.removed
    assert hass.config_entries.reloaded == ["entry-1"]


def test_integration_unload_entry_stops_on_platform_unload_failure() -> None:
    hass = FakeHass()

    async def _unload_platforms(entry: Any, platforms: tuple[str, ...]) -> bool:
        return False

    hass.config_entries.async_unload_platforms = _unload_platforms  # type: ignore[method-assign]
    hass.services.registered[("teltonika_rms", "refresh")] = object()

    assert asyncio.run(integration.async_unload_entry(hass, SimpleNamespace(entry_id="entry-1"))) is False
    assert hass.services.removed == []


def test_integration_setup_entry_pat_and_oauth_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeApi:
        def __init__(self, auth: Any, endpoint_matrix: Any) -> None:
            self.auth = auth
            self.endpoint_matrix = endpoint_matrix
            self.request_counter = 0
            self.status_manager = None

        def set_status_channel_manager(self, manager: Any) -> None:
            self.status_manager = manager

        async def async_validate_connection(self) -> None:
            return None

    class FakeCoordinator:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            self.data: dict[str, Any] = {}
            self.update_interval = timedelta(seconds=120)

        async def async_config_entry_first_refresh(self) -> None:
            return None

    class FakeStatusManager:
        def __init__(self, api: Any) -> None:
            self.api = api

    hass = FakeHass()
    hass.config_entries.entries_result = [object()]

    monkeypatch.setattr("teltonika_rms.endpoint_matrix.load_endpoint_matrix", lambda path: _test_matrix())
    monkeypatch.setattr("teltonika_rms.api.PatRmsAuthClient", lambda session, token: ("pat", session, token))
    monkeypatch.setattr("teltonika_rms.api.RmsApiClient", FakeApi)
    monkeypatch.setattr("teltonika_rms.coordinator.InventoryCoordinator", FakeCoordinator)
    monkeypatch.setattr("teltonika_rms.coordinator.StateCoordinator", FakeCoordinator)
    monkeypatch.setattr("teltonika_rms.coordinator.PortScanCoordinator", FakeCoordinator)
    monkeypatch.setattr("teltonika_rms.coordinator.PortConfigCoordinator", FakeCoordinator)
    monkeypatch.setattr("teltonika_rms.status_channel.RmsStatusChannelManager", FakeStatusManager)
    monkeypatch.setattr(
        "homeassistant.helpers.aiohttp_client.async_get_clientsession",
        lambda hass: "session",
    )

    entry = SimpleNamespace(
        data={CONF_AUTH_MODE: AUTH_MODE_PAT, CONF_PAT_TOKEN: "pat-token"},
        options={},
        runtime_data=None,
        entry_id="entry-1",
        add_update_listener=lambda listener: "listener-token",
        async_on_unload=lambda cb: None,
    )

    assert asyncio.run(integration.async_setup_entry(hass, entry)) is True
    assert entry.runtime_data is not None
    assert hass.config_entries.forwarded
    assert ("teltonika_rms", "refresh") in hass.services.registered

    missing_pat = SimpleNamespace(
        data={CONF_AUTH_MODE: AUTH_MODE_PAT, CONF_PAT_TOKEN: " "},
        options={},
    )
    with pytest.raises(ConfigEntryNotReady, match="PAT token missing"):
        asyncio.run(integration.async_setup_entry(hass, missing_pat))

    from homeassistant.helpers import config_entry_oauth2_flow

    async def _impl_error(_hass: Any, _entry: Any) -> Any:
        raise config_entry_oauth2_flow.ImplementationUnavailableError("missing")

    monkeypatch.setattr(
        "homeassistant.helpers.config_entry_oauth2_flow.async_get_config_entry_implementation",
        _impl_error,
    )
    oauth_entry = SimpleNamespace(data={CONF_AUTH_MODE: AUTH_MODE_OAUTH2}, options={})
    with pytest.raises(ConfigEntryNotReady, match="OAuth implementation unavailable"):
        asyncio.run(integration.async_setup_entry(hass, oauth_entry))


def test_integration_setup_entry_wraps_refresh_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeApi:
        def __init__(self, auth: Any, endpoint_matrix: Any) -> None:
            self.endpoint_matrix = endpoint_matrix

        def set_status_channel_manager(self, manager: Any) -> None:
            return None

        async def async_validate_connection(self) -> None:
            return None

    class FailingCoordinator:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            self.data = {}
            self.update_interval = timedelta(seconds=120)

        async def async_config_entry_first_refresh(self) -> None:
            raise RuntimeError("boom")

    monkeypatch.setattr("teltonika_rms.endpoint_matrix.load_endpoint_matrix", lambda path: _test_matrix())
    monkeypatch.setattr("teltonika_rms.api.PatRmsAuthClient", lambda session, token: ("pat", session, token))
    monkeypatch.setattr("teltonika_rms.api.RmsApiClient", FakeApi)
    monkeypatch.setattr("teltonika_rms.coordinator.InventoryCoordinator", FailingCoordinator)
    monkeypatch.setattr("teltonika_rms.coordinator.StateCoordinator", FailingCoordinator)
    monkeypatch.setattr("teltonika_rms.coordinator.PortScanCoordinator", FailingCoordinator)
    monkeypatch.setattr("teltonika_rms.coordinator.PortConfigCoordinator", FailingCoordinator)
    monkeypatch.setattr("teltonika_rms.status_channel.RmsStatusChannelManager", lambda api: SimpleNamespace(api=api))
    monkeypatch.setattr("homeassistant.helpers.aiohttp_client.async_get_clientsession", lambda hass: "session")

    hass = FakeHass()
    entry = SimpleNamespace(
        data={CONF_AUTH_MODE: AUTH_MODE_PAT, CONF_PAT_TOKEN: "pat-token"},
        options={},
        runtime_data=None,
        entry_id="entry-1",
        add_update_listener=lambda listener: "listener-token",
        async_on_unload=lambda cb: None,
    )

    with pytest.raises(ConfigEntryNotReady, match="Failed to initialize Teltonika RMS: boom"):
        asyncio.run(integration.async_setup_entry(hass, entry))


def test_integration_setup_entry_propagates_auth_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeApi:
        def __init__(self, auth: Any, endpoint_matrix: Any) -> None:
            self.endpoint_matrix = endpoint_matrix

        def set_status_channel_manager(self, manager: Any) -> None:
            return None

        async def async_validate_connection(self) -> None:
            raise ConfigEntryAuthFailed("denied")

    class FakeCoordinator:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            self.data = {}
            self.update_interval = timedelta(seconds=120)

        async def async_config_entry_first_refresh(self) -> None:
            return None

    monkeypatch.setattr("teltonika_rms.endpoint_matrix.load_endpoint_matrix", lambda path: _test_matrix())
    monkeypatch.setattr("teltonika_rms.api.PatRmsAuthClient", lambda session, token: ("pat", session, token))
    monkeypatch.setattr("teltonika_rms.api.RmsApiClient", FakeApi)
    monkeypatch.setattr("teltonika_rms.coordinator.InventoryCoordinator", FakeCoordinator)
    monkeypatch.setattr("teltonika_rms.coordinator.StateCoordinator", FakeCoordinator)
    monkeypatch.setattr("teltonika_rms.coordinator.PortScanCoordinator", FakeCoordinator)
    monkeypatch.setattr("teltonika_rms.coordinator.PortConfigCoordinator", FakeCoordinator)
    monkeypatch.setattr("teltonika_rms.status_channel.RmsStatusChannelManager", lambda api: SimpleNamespace(api=api))
    monkeypatch.setattr("homeassistant.helpers.aiohttp_client.async_get_clientsession", lambda hass: "session")

    hass = FakeHass()
    entry = SimpleNamespace(
        data={CONF_AUTH_MODE: AUTH_MODE_PAT, CONF_PAT_TOKEN: "pat-token"},
        options={},
        runtime_data=None,
        entry_id="entry-1",
        add_update_listener=lambda listener: "listener-token",
        async_on_unload=lambda cb: None,
    )

    with pytest.raises(ConfigEntryAuthFailed):
        asyncio.run(integration.async_setup_entry(hass, entry))


def test_integration_setup_returns_true() -> None:
    with tempfile.TemporaryDirectory() as _tmp:
        assert asyncio.run(integration.async_setup(SimpleNamespace(), {})) is True
