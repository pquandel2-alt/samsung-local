"""Dynamically discovered Samsung Local sensors."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory
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
            SamsungLocalSensor(coordinator, capability) for capability in capabilities
        )

    coordinator.register_platform(EntityPlatform.SENSOR, add)
    add(
        [
            capability
            for capability in coordinator.data.capabilities.values()
            if capability.platform is EntityPlatform.SENSOR
        ]
    )


class SamsungLocalSensor(SamsungLocalEntity, SensorEntity):
    def __init__(self, coordinator: SamsungLocalCoordinator, capability: Capability) -> None:
        super().__init__(coordinator, capability)
        self._attr_native_unit_of_measurement = capability.unit
        self._attr_device_class = (
            SensorDeviceClass(capability.device_class) if capability.device_class else None
        )
        self._attr_state_class = (
            SensorStateClass(capability.state_class) if capability.state_class else None
        )
        self._attr_options = list(capability.options) or None
        self._attr_entity_category = (
            EntityCategory(capability.entity_category) if capability.entity_category else None
        )

    @property
    def native_value(self) -> Any:
        capability = self.capability
        return capability.value if capability else None
