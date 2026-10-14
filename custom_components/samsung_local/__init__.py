"""Samsung Local Home Assistant integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .connection.manager import ConnectionManager
from .const import (
    CONF_AUTO_RECONNECT,
    CONF_POLL_INTERVAL,
    DEFAULT_AUTO_RECONNECT,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import SamsungLocalCoordinator
from .runtime import build_adapter
from .services import async_register_services, async_unregister_services

_LOADED_ENTRIES = f"{DOMAIN}_loaded_entries"

type SamsungLocalConfigEntry = ConfigEntry[SamsungLocalCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: SamsungLocalConfigEntry) -> bool:
    """Set up one physical Samsung device."""
    adapter = build_adapter(hass, entry)
    manager = ConnectionManager(
        adapter,
        auto_reconnect=entry.options.get(CONF_AUTO_RECONNECT, DEFAULT_AUTO_RECONNECT),
    )
    interval = int(entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL))
    coordinator = SamsungLocalCoordinator(
        hass,
        entry,
        manager,
        timedelta(seconds=interval),
    )
    await coordinator.async_initialize()
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        fallback = adapter.get_fallback_state()
        if fallback is None or manager.telemetry.last_error == "AuthenticationError":
            raise
        coordinator.async_set_updated_data(fallback)
    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    loaded_entries: set[str] = hass.data.setdefault(_LOADED_ENTRIES, set())
    loaded_entries.add(entry.entry_id)
    async_register_services(hass)
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: SamsungLocalConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: SamsungLocalConfigEntry) -> bool:
    """Unload entities before closing the shared connection."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_shutdown()
        loaded_entries: set[str] = hass.data.get(_LOADED_ENTRIES, set())
        loaded_entries.discard(entry.entry_id)
        if not loaded_entries:
            async_unregister_services(hass)
    return unloaded


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: SamsungLocalConfigEntry, device_entry: object
) -> bool:
    """Allow removal; each entry owns exactly one physical device."""
    return True
