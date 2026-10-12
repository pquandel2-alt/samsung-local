"""Dynamically discovered Samsung Local switches."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SamsungLocalConfigEntry
from .entity import SamsungLocalEntity
from .models import Capability, EntityPlatform


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SamsungLocalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data

    def add(capabilities: list[Capability]) -> None:
        async_add_entities(
            SamsungLocalSwitch(coordinator, capability) for capability in capabilities
        )

    coordinator.register_platform(EntityPlatform.SWITCH, add)
    add(
        [
            capability
            for capability in coordinator.data.capabilities.values()
            if capability.platform is EntityPlatform.SWITCH
        ]
    )


class SamsungLocalSwitch(SamsungLocalEntity, SwitchEntity):
    @property
    def is_on(self) -> bool | None:
        capability = self.capability
        return bool(capability.value) if capability and capability.value is not None else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_command(self.capability_key, value=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_command(self.capability_key, value=False)
