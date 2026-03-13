"""Teltonika RMS integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING, Any

from .const import (
    AUTH_MODE_OAUTH2,
    AUTH_MODE_PAT,
    CONF_AUTH_MODE,
    CONF_PAT_TOKEN,
    CONF_SPEC_PATH,
    DEFAULT_OPTIONS,
    DEFAULT_SPEC_PATH,
    DOMAIN,
    SERVICE_REFRESH,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

LOGGER = logging.getLogger(__name__)

try:
    from homeassistant.const import Platform

    PLATFORMS: tuple[str, ...] = (
        Platform.BINARY_SENSOR,
        Platform.SENSOR,
        Platform.DEVICE_TRACKER,
        Platform.BUTTON,
        Platform.UPDATE,
    )
except ModuleNotFoundError:
    PLATFORMS = ("binary_sensor", "sensor", "device_tracker", "button", "update")


@dataclass(slots=True)
class TeltonikaRmsRuntime:
    """Runtime data attached to config entry."""

    bundle: Any
    remove_service_listener: Callable[[], None] | None = None

async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up integration domain."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: Any) -> bool:
    """Set up Teltonika RMS from config entry."""
    from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
    from homeassistant.helpers import config_entry_oauth2_flow
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    from .api import OAuth2RmsAuthClient, PatRmsAuthClient, RmsApiClient
    from .coordinator import CoordinatorBundle, InventoryCoordinator, PortScanCoordinator, StateCoordinator
    from .endpoint_matrix import load_endpoint_matrix
    from .status_channel import RmsStatusChannelManager

    auth_mode = str(entry.data.get(CONF_AUTH_MODE, AUTH_MODE_OAUTH2))
    if auth_mode == AUTH_MODE_PAT:
        pat_token = str(entry.data.get(CONF_PAT_TOKEN, "")).strip()
        if not pat_token:
            raise ConfigEntryNotReady("PAT token missing")
        auth_client = PatRmsAuthClient(async_get_clientsession(hass), pat_token)
    else:
        try:
            implementation = await config_entry_oauth2_flow.async_get_config_entry_implementation(
                hass, entry
            )
        except config_entry_oauth2_flow.ImplementationUnavailableError as err:
            raise ConfigEntryNotReady(f"OAuth implementation unavailable: {err}") from err
        oauth_session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)
        auth_client = OAuth2RmsAuthClient(oauth_session)

    spec_path = str(entry.options.get(CONF_SPEC_PATH, DEFAULT_SPEC_PATH))
    endpoint_matrix = await hass.async_add_executor_job(load_endpoint_matrix, spec_path)

    api = RmsApiClient(
        auth=auth_client,
        endpoint_matrix=endpoint_matrix,
    )
    status_manager = RmsStatusChannelManager(api)
    api.set_status_channel_manager(status_manager)

    inventory = InventoryCoordinator(hass, api, _merged_options(entry))
    state = StateCoordinator(hass, api, inventory, _merged_options(entry))
    port_scan = PortScanCoordinator(hass, api, inventory)
    bundle = CoordinatorBundle(
        inventory=inventory,
        state=state,
        port_scan=port_scan,
        status_channels=status_manager,
        api=api,
    )

    entry.runtime_data = TeltonikaRmsRuntime(bundle=bundle)

    try:
        await api.async_validate_connection()
        await inventory.async_config_entry_first_refresh()
        await state.async_config_entry_first_refresh()
        await port_scan.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed:
        raise
    except Exception as err:
        raise ConfigEntryNotReady(f"Failed to initialize Teltonika RMS: {err}") from err

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    if not hass.services.has_service(DOMAIN, SERVICE_REFRESH):
        hass.services.async_register(DOMAIN, SERVICE_REFRESH, _build_refresh_handler(hass))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: Any) -> bool:
    """Unload Teltonika RMS entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    if not hass.config_entries.async_entries(DOMAIN):
        hass.services.async_remove(DOMAIN, SERVICE_REFRESH)
    return True


async def async_reload_entry(hass: HomeAssistant, entry: Any) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


def _build_refresh_handler(hass: HomeAssistant):
    from .coordinator import async_refresh_all

    async def _async_handle_refresh(call: Any) -> None:
        entries = hass.config_entries.async_entries(DOMAIN)
        for entry in entries:
            runtime: TeltonikaRmsRuntime | None = getattr(entry, "runtime_data", None)
            if runtime is None:
                continue
            await async_refresh_all(runtime.bundle)

    return _async_handle_refresh


def _merged_options(entry: Any) -> dict[str, Any]:
    merged = dict(DEFAULT_OPTIONS)
    merged.update(entry.options)
    return merged
