"""The Porsche Mobile Charger Connect integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_HOST, CONF_PASSWORD, DOMAIN
from .coordinator import PmccCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.NUMBER,
]

type PmccConfigEntry = ConfigEntry[PmccCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: PmccConfigEntry) -> bool:
    """Set up Porsche Mobile Charger Connect from a config entry."""
    coordinator = PmccCoordinator(
        hass,
        entry,
        host=entry.data[CONF_HOST],
        password=entry.data.get(CONF_PASSWORD),
    )
    await coordinator.async_start()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PmccConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_shutdown()
    return unloaded
