"""Generic climate surface for future capability-discovered Samsung HVAC."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import HVACMode
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
            SamsungLocalClimate(coordinator, capability) for capability in capabilities
        )

    coordinator.register_platform(EntityPlatform.CLIMATE, add)
    add(
        [
            capability
            for capability in coordinator.data.capabilities.values()
            if capability.platform is EntityPlatform.CLIMATE
        ]
    )


class SamsungLocalClimate(SamsungLocalEntity, ClimateEntity):
    @property
    def current_temperature(self) -> float | None:
        capability = self.capability
        value = capability.attributes.get("current_temperature") if capability else None
        return float(value) if value is not None else None

    @property
    def target_temperature(self) -> float | None:
        capability = self.capability
        value = capability.attributes.get("target_temperature") if capability else None
        return float(value) if value is not None else None

    @property
    def hvac_mode(self) -> HVACMode | None:
        capability = self.capability
        value = capability.attributes.get("hvac_mode") if capability else None
        return HVACMode(str(value)) if value is not None else None

    @property
    def hvac_modes(self) -> list[HVACMode]:
        capability = self.capability
        return (
            [HVACMode(str(value)) for value in capability.attributes.get("hvac_modes", ())]
            if capability
            else []
        )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        await self._async_command(self.capability_key, value=kwargs.get("temperature"))

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        await self._async_command(self.capability_key, mode=hvac_mode)
