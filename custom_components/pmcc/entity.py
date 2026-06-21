"""Shared base entity for the Porsche Mobile Charger Connect."""

from __future__ import annotations

from homeassistant.helpers.device_info import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PmccCoordinator


class PmccEntity(CoordinatorEntity[PmccCoordinator]):
    """Base entity binding everything to one charger device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PmccCoordinator) -> None:
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        model = coordinator.data.get("de.bebro.SCC.name.model")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="Porsche Mobile Charger Connect",
            manufacturer="Porsche",
            model=str(model) if model else "Mobile Charger Connect",
            configuration_url=f"https://{coordinator.host}/",
        )
