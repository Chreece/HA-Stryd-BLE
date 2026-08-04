"""StrydX BLE integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import PLATFORMS
from .coordinator import StrydXCoordinator
from .naming import async_migrate_entity_ids


type StrydXConfigEntry = ConfigEntry[StrydXCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: StrydXConfigEntry) -> bool:
    """Set up StrydX BLE from a config entry."""
    coordinator = StrydXCoordinator(hass, entry)
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator.async_start()
    await async_migrate_entity_ids(hass, entry, coordinator.data.product_name)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: StrydXConfigEntry) -> bool:
    """Unload a StrydX BLE config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_stop()
    return unloaded
