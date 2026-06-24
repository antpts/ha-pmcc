"""Sensor platform: one entity per metric in the registry."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import PmccConfigEntry
from .const import KEY_TOTAL_ENERGY, METRICS, SOC_UNKNOWN
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
    for key, cfg in METRICS.items():
        description = _build_description(key, cfg)
        if key == KEY_TOTAL_ENERGY:
            entities.append(PmccTotalEnergy(coordinator, description))
        else:
            entities.append(PmccSensor(coordinator, description))
    async_add_entities(entities)


class PmccSensor(PmccEntity, SensorEntity):
    """A single charger metric."""

    def __init__(
        self, coordinator: PmccCoordinator, description: SensorEntityDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        # Sensors with a state_class must yield numbers (HA rejects strings and
        # spams the log otherwise), so coerce/parse rather than pass through.
        self._numeric = description.state_class is not None

    @property
    def native_value(self) -> Any:
        value = self.coordinator.data.get(self.entity_description.key)
        if value is None:
            return None
        # SoC fields report -1 when the vehicle doesn't share state of charge.
        if (
            self.entity_description.device_class == SensorDeviceClass.BATTERY
            and value == SOC_UNKNOWN
        ):
            return None
        if self._numeric:
            return self._to_number(value, self.entity_description.device_class)
        if isinstance(value, (dict, list)):
            return json.dumps(value, separators=(",", ":"))[:_MAX_STATE_LEN]
        if isinstance(value, str):
            return value[:_MAX_STATE_LEN]
        return value

    @staticmethod
    def _to_number(value: Any, device_class: SensorDeviceClass | None) -> float | None:
        """Coerce a charger value to a number, or None if it isn't one.

        Handles the charger's quirks: empty strings (e.g. unset costs) and the
        "H:MM:SS" duration string (e.g. total charging time) -> seconds.
        """
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return value
        if not isinstance(value, str):
            return None
        text = value.strip()
        if not text:
            return None
        if device_class == SensorDeviceClass.DURATION and ":" in text:
            try:
                seconds = 0
                for part in text.split(":"):
                    seconds = seconds * 60 + int(part)
                return seconds
            except ValueError:
                return None
        try:
            return float(text)
        except ValueError:
            return None


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


class PmccTotalEnergy(PmccEntity, RestoreSensor):
    """Lifetime charging energy (live), but holds its last value.

    The charger only streams this while awake/charging and then sleeps/drops
    WiFi. Rather than going unavailable, this sensor keeps showing the last
    value, restores it across restarts, and never decreases (it's a
    total_increasing meter).
    """

    _attr_suggested_display_precision = 3

    def __init__(
        self, coordinator: PmccCoordinator, description: SensorEntityDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._restored: float | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_sensor_data()
        if last is not None and last.native_value is not None:
            self._restored = float(last.native_value)

    @property
    def available(self) -> bool:
        # Hold the last reading even when the charger is asleep/offline.
        return True

    @property
    def native_value(self) -> float | None:
        live = self.coordinator.data.get(self.entity_description.key)
        candidates = []
        for v in (live, self._restored):
            if v is None:
                continue
            try:
                candidates.append(float(v))
            except (TypeError, ValueError):
                continue
        return max(candidates) if candidates else None
