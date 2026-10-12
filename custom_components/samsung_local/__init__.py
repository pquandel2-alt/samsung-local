"""Samsung Local Home Assistant integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .connection.manager import ConnectionManager
from .const import (
    CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    PLATFORMS,
)
from .coordinator import SamsungLocalCoordinator
from .runtime import build_adapter

type SamsungLocalConfigEntry = ConfigEntry[SamsungLocalCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: SamsungLocalConfigEntry) -> bool:
    """Set up one physical Samsung device."""
    adapter = build_adapter(hass, entry)
    manager = ConnectionManager(adapter)
    interval = int(entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL))
    coordinator = SamsungLocalCoordinator(
        hass,
        entry,
        manager,
        timedelta(seconds=interval),
    )
    await coordinator.async_initialize()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: SamsungLocalConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: SamsungLocalConfigEntry) -> bool:
    """Unload entities before closing the shared connection."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_shutdown()
    return unloaded


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: SamsungLocalConfigEntry, device_entry: object
) -> bool:
    """Allow removal; each entry owns exactly one physical device."""
    return True
