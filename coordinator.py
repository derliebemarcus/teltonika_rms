"""Coordinators for Teltonika RMS integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import RmsApiClient, estimate_monthly_requests, normalize_tags
from .const import (
    CONF_DEVICE_STATUS,
    CONF_ENABLE_LOCATION,
    CONF_ESTIMATED_DEVICES,
    CONF_INVENTORY_INTERVAL,
    CONF_STATE_INTERVAL,
    CONF_TAGS,
    DEFAULT_ESTIMATED_DEVICES,
    DEFAULT_INVENTORY_INTERVAL,
    DEFAULT_STATE_INTERVAL,
    MAX_MONTHLY_REQUESTS,
    REQUEST_BUDGET_HEADROOM,
)
from .exceptions import RmsApiError
from .models import NormalizedDevice, normalize_device
from .status_channel import RmsStatusChannelManager

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class CoordinatorBundle:
    """Runtime coordinators and helpers."""

    inventory: "InventoryCoordinator"
    state: "StateCoordinator"
    status_channels: RmsStatusChannelManager
    api: RmsApiClient

    def merged_device(self, device_id: str) -> NormalizedDevice | None:
        """Return merged normalized data for one device."""
        inventory_raw = self.inventory.data.get(device_id)
        if inventory_raw is None:
            return None
        state_raw = self.state.data.get(device_id, {})
        location_raw = state_raw.get("location") if isinstance(state_raw, dict) else {}
        base_state = state_raw.get("state") if isinstance(state_raw, dict) else {}
        return normalize_device(inventory_raw, base_state, location_raw)


class InventoryCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Fetches inventory data on lower cadence."""

    def __init__(self, hass: HomeAssistant, api: RmsApiClient, options: dict[str, Any]) -> None:
        self._api = api
        self._tags = normalize_tags(str(options.get(CONF_TAGS, "")))
        self._device_status = str(options.get(CONF_DEVICE_STATUS, "")).strip() or None
        interval = int(options.get(CONF_INVENTORY_INTERVAL, DEFAULT_INVENTORY_INTERVAL))
        super().__init__(
            hass,
            LOGGER,
            name="Teltonika RMS inventory",
            update_interval=timedelta(seconds=max(60, interval)),
        )

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            devices = await self._api.async_list_devices(
                tags=self._tags or None,
                device_status=self._device_status,
            )
        except ConfigEntryAuthFailed:
            raise
        except RmsApiError as err:
            raise UpdateFailed(f"Inventory refresh failed: {err}") from err

        normalized: dict[str, dict[str, Any]] = {}
        for raw in devices:
            record = normalize_device(raw)
            if record is None:
                continue
            normalized[record.device_id] = raw
        return normalized


class StateCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Fetches frequently changing state and location data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: RmsApiClient,
        inventory: InventoryCoordinator,
        options: dict[str, Any],
    ) -> None:
        self._api = api
        self._inventory = inventory
        self._enable_location = bool(options.get(CONF_ENABLE_LOCATION, True))
        self._estimated_devices = int(options.get(CONF_ESTIMATED_DEVICES, DEFAULT_ESTIMATED_DEVICES))
        self._state_interval = int(options.get(CONF_STATE_INTERVAL, DEFAULT_STATE_INTERVAL))
        super().__init__(
            hass,
            LOGGER,
            name="Teltonika RMS state",
            update_interval=timedelta(seconds=max(60, self._state_interval)),
        )

    @property
    def monthly_request_estimate(self) -> int:
        """Compute current monthly estimate from options."""
        aggregate_supported = self._api.endpoint_matrix.path_for("device_state_aggregate") is not None
        return estimate_monthly_requests(
            inventory_interval=int(self._inventory.update_interval.total_seconds()),
            state_interval=self._state_interval,
            estimated_devices=self._estimated_devices,
            aggregate_state_supported=aggregate_supported,
        )

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        device_ids = list(self._inventory.data.keys())
        if not device_ids:
            return {}

        max_per_cycle: int | None = None
        if self._api.endpoint_matrix.path_for("device_state_aggregate") is None:
            budget_based = self._api.estimate_max_calls_per_cycle(self._state_interval)
            max_per_cycle = max(1, budget_based - 1)

        try:
            state_map = await self._api.async_get_states_for_devices(
                device_ids,
                max_per_cycle=max_per_cycle,
            )
        except ConfigEntryAuthFailed:
            raise
        except RmsApiError as err:
            raise UpdateFailed(f"State refresh failed: {err}") from err

        results: dict[str, dict[str, Any]] = {}
        for device_id in device_ids:
            results[device_id] = {"state": state_map.get(device_id, {})}

        if self._enable_location:
            await self._async_enrich_locations(results, device_ids, max_per_cycle=max_per_cycle)

        self._log_budget_warning()
        return results

    async def _async_enrich_locations(
        self,
        results: dict[str, dict[str, Any]],
        device_ids: list[str],
        *,
        max_per_cycle: int | None,
    ) -> None:
        limit = len(device_ids) if max_per_cycle is None else max(1, max_per_cycle)
        for device_id in device_ids[:limit]:
            try:
                location = await self._api.async_get_device_location(device_id)
            except RmsApiError:
                location = {}
            if location:
                results.setdefault(device_id, {})["location"] = location

    def _log_budget_warning(self) -> None:
        estimate = self.monthly_request_estimate
        ceiling = int(MAX_MONTHLY_REQUESTS * REQUEST_BUDGET_HEADROOM)
        if estimate > ceiling:
            LOGGER.warning(
                "RMS estimated monthly requests (%s) exceed configured budget headroom (%s).",
                estimate,
                ceiling,
            )


async def async_refresh_all(bundle: CoordinatorBundle) -> None:
    """Run immediate refresh for both coordinators."""
    await bundle.inventory.async_request_refresh()
    await bundle.state.async_request_refresh()


def validate_request_budget(
    *,
    inventory_interval: int,
    state_interval: int,
    estimated_devices: int,
    aggregate_state_supported: bool,
) -> bool:
    """Budget gate used by options flow."""
    estimate = estimate_monthly_requests(
        inventory_interval=inventory_interval,
        state_interval=state_interval,
        estimated_devices=estimated_devices,
        aggregate_state_supported=aggregate_state_supported,
    )
    return estimate <= int(MAX_MONTHLY_REQUESTS * REQUEST_BUDGET_HEADROOM)
