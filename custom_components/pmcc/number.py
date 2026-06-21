"""Number platform: the charging current limit (requires a password)."""

from __future__ import annotations

import logging

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberMode,
)
from homeassistant.const import UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import PmccConfigEntry
from .const import MAX_CURRENT, MIN_CURRENT
from .coordinator import PmccCoordinator, PmccError
from .entity import PmccEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PmccConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the current-limit control if a password was configured."""
    coordinator = entry.runtime_data
    if coordinator.password:
        async_add_entities([PmccCurrentLimit(coordinator)])


class PmccCurrentLimit(PmccEntity, NumberEntity):
    """Charging current limit (0-16 A)."""

    _attr_translation_key = "current_limit"
    _attr_device_class = NumberDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_native_min_value = MIN_CURRENT
    _attr_native_max_value = MAX_CURRENT
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: PmccCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_current_limit"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.current_limit

    async def async_set_native_value(self, value: float) -> None:
        try:
            await self.coordinator.async_set_current_limit(int(value))
        except PmccError as err:
            raise HomeAssistantError(f"Could not set current limit: {err}") from err
