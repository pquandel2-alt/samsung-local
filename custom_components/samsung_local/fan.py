"""Generic fan surface for future capability-discovered Samsung air devices."""

from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity
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
        async_add_entities(SamsungLocalFan(coordinator, capability) for capability in capabilities)

    coordinator.register_platform(EntityPlatform.FAN, add)
    add(
        [
            capability
            for capability in coordinator.data.capabilities.values()
            if capability.platform is EntityPlatform.FAN
        ]
    )


class SamsungLocalFan(SamsungLocalEntity, FanEntity):
    @property
    def is_on(self) -> bool | None:
        capability = self.capability
        return bool(capability.value) if capability and capability.value is not None else None

    @property
    def percentage(self) -> int | None:
        capability = self.capability
        value = capability.attributes.get("percentage") if capability else None
        return int(value) if value is not None else None

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        await self._async_command(
            self.capability_key,
            value=True,
            percentage=percentage,
            preset_mode=preset_mode,
            **kwargs,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_command(self.capability_key, value=False)

    async def async_set_percentage(self, percentage: int) -> None:
        await self._async_command(self.capability_key, percentage=percentage)
