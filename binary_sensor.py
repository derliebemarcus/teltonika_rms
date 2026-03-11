"""Binary sensors for Teltonika RMS."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TeltonikaRmsRuntime
from .coordinator import CoordinatorBundle
from .entity import TeltonikaRmsEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime: TeltonikaRmsRuntime = entry.runtime_data
    bundle: CoordinatorBundle = runtime.bundle
    known: set[str] = set()

    @callback
    def _add_new_entities() -> None:
        new_entities: list[RmsOnlineBinarySensor] = []
        for device_id in bundle.inventory.data:
            unique = f"{device_id}_online"
            if unique in known:
                continue
            known.add(unique)
            new_entities.append(RmsOnlineBinarySensor(bundle, device_id))
        if new_entities:
            async_add_entities(new_entities)

    _add_new_entities()
    entry.async_on_unload(bundle.inventory.async_add_listener(_add_new_entities))


class RmsOnlineBinarySensor(TeltonikaRmsEntity, BinarySensorEntity):
    """Connectivity state for an RMS device."""

    _attr_translation_key = "online"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_icon = "mdi:router-network"

    def __init__(self, bundle: CoordinatorBundle, device_id: str) -> None:
        super().__init__(bundle, device_id)
        self._attr_unique_id = f"{device_id}_online"

    @property
    def is_on(self) -> bool | None:
        normalized = self._normalized
        return normalized.online if normalized else None
