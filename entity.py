"""Base entity for Teltonika RMS."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CoordinatorBundle
from .models import NormalizedDevice


class TeltonikaRmsEntity(CoordinatorEntity):
    """Base coordinator entity bound to one RMS device."""

    _attr_has_entity_name = True

    def __init__(self, bundle: CoordinatorBundle, device_id: str) -> None:
        super().__init__(bundle.state)
        self._bundle = bundle
        self._device_id = device_id

    @property
    def device_id(self) -> str:
        """RMS device identifier."""
        return self._device_id

    @property
    def _normalized(self) -> NormalizedDevice | None:
        return self._bundle.merged_device(self._device_id)

    @property
    def available(self) -> bool:
        return self._normalized is not None

    @property
    def device_info(self) -> dict[str, Any] | None:
        normalized = self._normalized
        if normalized is None:
            return None
        info: dict[str, Any] = {
            "identifiers": {(DOMAIN, self._device_id)},
            "manufacturer": "Teltonika",
            "name": normalized.name,
            "model": normalized.model,
            "sw_version": normalized.firmware,
            "serial_number": normalized.serial,
        }
        return info

