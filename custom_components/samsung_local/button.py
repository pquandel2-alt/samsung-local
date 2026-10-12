"""Dynamically discovered Samsung Local action buttons."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
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
            SamsungLocalButton(coordinator, capability) for capability in capabilities
        )

    coordinator.register_platform(EntityPlatform.BUTTON, add)
    add(
        [
            capability
            for capability in coordinator.data.capabilities.values()
            if capability.platform is EntityPlatform.BUTTON
        ]
    )


class SamsungLocalButton(SamsungLocalEntity, ButtonEntity):
    async def async_press(self) -> None:
        await self._async_command(self.capability_key)
