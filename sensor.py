"""Diagnostic sensors for Teltonika RMS."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
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
        new_entities: list[SensorEntity] = []
        for device_id in bundle.inventory.data:
            for key in ("model", "firmware", "serial", "last_seen"):
                unique = f"{device_id}_{key}"
                if unique in known:
                    continue
                known.add(unique)
                if key == "model":
                    new_entities.append(RmsModelSensor(bundle, device_id))
                elif key == "firmware":
                    new_entities.append(RmsFirmwareSensor(bundle, device_id))
                elif key == "last_seen":
                    new_entities.append(RmsLastSeenSensor(bundle, device_id))
                else:
                    new_entities.append(RmsSerialSensor(bundle, device_id))
        if new_entities:
            async_add_entities(new_entities)

    _add_new_entities()
    entry.async_on_unload(bundle.inventory.async_add_listener(_add_new_entities))


class _BaseDiagnosticSensor(TeltonikaRmsEntity, SensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, bundle: CoordinatorBundle, device_id: str, key: str) -> None:
        super().__init__(bundle, device_id)
        self._key = key
        self._attr_unique_id = f"{device_id}_{key}"

    @property
    def native_value(self) -> str | None:
        normalized = self._normalized
        if normalized is None:
            return None
        return getattr(normalized, self._key)


class RmsModelSensor(_BaseDiagnosticSensor):
    _attr_translation_key = "model"
    _attr_icon = "mdi:chip"

    def __init__(self, bundle: CoordinatorBundle, device_id: str) -> None:
        super().__init__(bundle, device_id, "model")


class RmsFirmwareSensor(_BaseDiagnosticSensor):
    _attr_translation_key = "firmware"
    _attr_icon = "mdi:update"

    def __init__(self, bundle: CoordinatorBundle, device_id: str) -> None:
        super().__init__(bundle, device_id, "firmware")


class RmsSerialSensor(_BaseDiagnosticSensor):
    _attr_translation_key = "serial"
    _attr_icon = "mdi:identifier"

    def __init__(self, bundle: CoordinatorBundle, device_id: str) -> None:
        super().__init__(bundle, device_id, "serial")


class RmsLastSeenSensor(TeltonikaRmsEntity, SensorEntity):
    """Last update timestamp from RMS."""

    _attr_translation_key = "last_seen"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:clock-check-outline"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, bundle: CoordinatorBundle, device_id: str) -> None:
        super().__init__(bundle, device_id)
        self._attr_unique_id = f"{device_id}_last_seen"

    @property
    def native_value(self) -> datetime | None:
        normalized = self._normalized
        return normalized.last_seen if normalized else None
