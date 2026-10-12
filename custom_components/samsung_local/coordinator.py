"""Home Assistant state coordinator for all Samsung Local protocols."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .completion import CompletionTracker
from .connection.manager import ConnectionManager
from .const import DOMAIN, EVENT_PROGRAM_FINISHED, LOGGER, STORAGE_KEY, STORAGE_VERSION
from .exceptions import AuthenticationError, CannotConnectError
from .models import Capability, DeviceSnapshot, EntityPlatform

EntityAdder = Callable[[list[Capability]], None]


class SamsungLocalCoordinator(DataUpdateCoordinator[DeviceSnapshot]):
    """Coordinate confirmed state and protocol push notifications."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        manager: ConnectionManager,
        update_interval: timedelta,
    ) -> None:
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}-{entry.entry_id}",
            update_interval=update_interval,
            always_update=True,
        )
        self.manager = manager
        self._platform_adders: dict[EntityPlatform, list[EntityAdder]] = {}
        self._known_capabilities: set[str] = set()
        self._store = Store[dict[str, bool]](
            hass, STORAGE_VERSION, f"{STORAGE_KEY}.{entry.entry_id}"
        )
        self._completion = CompletionTracker(save=self._async_save_finished)
        manager.adapter.set_update_callback(self._async_push_update)

    async def async_initialize(self) -> None:
        stored = await self._store.async_load() or {}
        self._completion.finished = bool(stored.get("finished", False))

    async def _async_save_finished(self, value: bool) -> None:
        await self._store.async_save({"finished": value})

    async def _async_update_data(self) -> DeviceSnapshot:
        try:
            snapshot = await self.manager.async_update()
        except AuthenticationError as err:
            self.config_entry.async_start_reauth(self.hass)
            raise UpdateFailed("local authentication failed") from err
        except CannotConnectError as err:
            raise UpdateFailed(str(err)) from err
        await self._async_process_snapshot(snapshot)
        return snapshot

    async def _async_push_update(self, snapshot: DeviceSnapshot) -> None:
        await self._async_process_snapshot(snapshot)
        self.async_set_updated_data(snapshot)

    async def _async_process_snapshot(self, snapshot: DeviceSnapshot) -> None:
        current_keys = set(snapshot.capabilities)
        new_keys = current_keys - self._known_capabilities
        self._known_capabilities |= current_keys
        issue_id = f"unknown_capabilities_{self.config_entry.entry_id}"
        if snapshot.unknown_capabilities:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="unknown_capabilities",
                translation_placeholders={
                    "device": snapshot.info.model or snapshot.info.category.value,
                    "count": str(len(snapshot.unknown_capabilities)),
                },
            )
        else:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)
        if new_keys:
            by_platform: dict[EntityPlatform, list[Capability]] = {}
            for key in sorted(new_keys):
                capability = snapshot.capabilities[key]
                by_platform.setdefault(capability.platform, []).append(capability)
            for platform, capabilities in by_platform.items():
                for adder in self._platform_adders.get(platform, ()):
                    adder(capabilities)
        machine = snapshot.capability("machine_state")
        progress = snapshot.capability("program_progress")
        program = snapshot.capability("program")
        if await self._completion.async_update(
            str(machine.value) if machine else None,
            str(progress.value) if progress else None,
        ):
            self.hass.bus.async_fire(
                EVENT_PROGRAM_FINISHED,
                {
                    "device_id": snapshot.info.device_id,
                    "model": snapshot.info.model,
                    "program": program.value if program else None,
                },
            )

    def register_platform(self, platform: EntityPlatform, adder: EntityAdder) -> None:
        self._platform_adders.setdefault(platform, []).append(adder)

    async def async_command(self, command: str, **kwargs: Any) -> None:
        await self.manager.async_execute(command, **kwargs)
        await self.async_request_refresh()

    async def async_shutdown(self) -> None:
        self.manager.adapter.set_update_callback(None)
        await self.manager.async_disconnect()
