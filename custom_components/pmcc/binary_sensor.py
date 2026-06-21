"""Binary sensor platform: charger connectivity."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import PmccConfigEntry
from .coordinator import PmccCoordinator
from .entity import PmccEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PmccConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the connectivity binary sensor."""
    async_add_entities([PmccConnectivity(entry.runtime_data)])


class PmccConnectivity(PmccEntity, BinarySensorEntity):
    """Whether the WebSocket link to the charger is up."""

    _attr_translation_key = "connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PmccCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_connected"

    @property
    def available(self) -> bool:
        # Always report — its whole purpose is to show up/down state.
        return True

    @property
    def is_on(self) -> bool:
        return self.coordinator.connected
