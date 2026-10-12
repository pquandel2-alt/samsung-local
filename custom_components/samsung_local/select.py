"""Dynamically discovered Samsung Local selects."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
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
            SamsungLocalSelect(coordinator, capability) for capability in capabilities
        )

    coordinator.register_platform(EntityPlatform.SELECT, add)
    add(
        [
            capability
            for capability in coordinator.data.capabilities.values()
            if capability.platform is EntityPlatform.SELECT
        ]
    )


class SamsungLocalSelect(SamsungLocalEntity, SelectEntity):
    @property
    def current_option(self) -> str | None:
        capability = self.capability
        return str(capability.value) if capability and capability.value is not None else None

    @property
    def options(self) -> list[str]:
        capability = self.capability
        return list(capability.options) if capability else []

    async def async_select_option(self, option: str) -> None:
        await self._async_command(self.capability_key, value=option)
