"""Sensor platform: one entity per metric in the registry."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import PmccConfigEntry
from .const import METRICS
from .coordinator import PmccCoordinator
from .entity import PmccEntity

# HA caps state strings at 255 chars.
_MAX_STATE_LEN = 255


def _build_description(key: str, cfg: dict[str, Any]) -> SensorEntityDescription:
    """Translate a registry entry into a SensorEntityDescription."""
    unit = cfg.get("unit")
    # A device_class only makes sense with a matching unit; skip it otherwise
    # to avoid Home Assistant validation warnings (e.g. duration w/o unit).
    device_class = (
        SensorDeviceClass(cfg["device_class"])
        if cfg.get("device_class") and unit
        else None
    )
    state_class = (
        SensorStateClass(cfg["state_class"]) if cfg.get("state_class") else None
    )
    entity_category = (
        EntityCategory(cfg["entity_category"]) if cfg.get("entity_category") else None
    )
    return SensorEntityDescription(
        key=key,
        name=cfg.get("pretty_name", key.split(".")[-1]),
        native_unit_of_measurement=unit,
        device_class=device_class,
        state_class=state_class,
        entity_category=entity_category,
        # Named metrics are useful; unnamed ones are mostly debug noise.
        entity_registry_enabled_default=cfg.get(
            "enabled_by_default", "pretty_name" in cfg
        ),
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PmccConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create sensors for every known metric, plus a last-update timestamp."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [PmccLastUpdate(coordinator)]
    entities.extend(
        PmccSensor(coordinator, _build_description(key, cfg))
        for key, cfg in METRICS.items()
    )
    async_add_entities(entities)


class PmccSensor(PmccEntity, SensorEntity):
    """A single charger metric."""

    def __init__(
        self, coordinator: PmccCoordinator, description: SensorEntityDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        value = self.coordinator.data.get(self.entity_description.key)
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return json.dumps(value, separators=(",", ":"))[:_MAX_STATE_LEN]
        if isinstance(value, str):
            return value[:_MAX_STATE_LEN]
        return value


class PmccLastUpdate(PmccEntity, SensorEntity):
    """Timestamp of the most recent message received from the charger."""

    _attr_translation_key = "last_update"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PmccCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_last_update"

    @property
    def available(self) -> bool:
        # Keep showing the last-seen time even while the link is down.
        return True

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.last_message_time
