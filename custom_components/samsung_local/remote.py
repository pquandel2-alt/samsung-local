"""Samsung Tizen remote entity."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from homeassistant.components.remote import ATTR_NUM_REPEATS, RemoteEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SamsungLocalConfigEntry
from .entity import SamsungLocalEntity
from .models import Capability, ConnectionStatus, EntityPlatform

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SamsungLocalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data

    def add(capabilities: list[Capability]) -> None:
        async_add_entities(
            SamsungLocalRemote(coordinator, capability) for capability in capabilities
        )

    coordinator.register_platform(EntityPlatform.REMOTE, add)
    add(
        [
            capability
            for capability in coordinator.data.capabilities.values()
            if capability.platform is EntityPlatform.REMOTE
        ]
    )


class SamsungLocalRemote(SamsungLocalEntity, RemoteEntity):
    @property
    def is_on(self) -> bool:
        return self.coordinator.data.connection is ConnectionStatus.CONNECTED

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_command("power_on")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_command("power_off")

    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        repeats = int(kwargs.get(ATTR_NUM_REPEATS, 1))
        for _ in range(repeats):
            for key in command:
                await self._async_command("remote_key", value=key)
