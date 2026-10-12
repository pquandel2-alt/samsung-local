"""Dynamically discovered Samsung Local numeric controls."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SamsungLocalConfigEntry
from .coordinator import SamsungLocalCoordinator
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
            SamsungLocalNumber(coordinator, capability) for capability in capabilities
        )

    coordinator.register_platform(EntityPlatform.NUMBER, add)
    add(
        [
            capability
            for capability in coordinator.data.capabilities.values()
            if capability.platform is EntityPlatform.NUMBER
        ]
    )


class SamsungLocalNumber(SamsungLocalEntity, NumberEntity):
    def __init__(self, coordinator: SamsungLocalCoordinator, capability: Capability) -> None:
        super().__init__(coordinator, capability)
        self._attr_native_min_value = capability.native_min or 0
        self._attr_native_max_value = capability.native_max or 100
        self._attr_native_step = capability.native_step or 1
        self._attr_native_unit_of_measurement = capability.unit
        self._attr_device_class = (
            NumberDeviceClass(capability.device_class) if capability.device_class else None
        )

    @property
    def native_value(self) -> float | None:
        capability = self.capability
        return float(capability.value) if capability and capability.value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        await self._async_command(self.capability_key, value=value)
