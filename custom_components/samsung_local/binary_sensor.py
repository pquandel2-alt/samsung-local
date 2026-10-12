"""Dynamically discovered Samsung Local binary sensors."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
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
            SamsungLocalBinarySensor(coordinator, capability) for capability in capabilities
        )

    coordinator.register_platform(EntityPlatform.BINARY_SENSOR, add)
    add(
        [
            capability
            for capability in coordinator.data.capabilities.values()
            if capability.platform is EntityPlatform.BINARY_SENSOR
        ]
    )


class SamsungLocalBinarySensor(SamsungLocalEntity, BinarySensorEntity):
    def __init__(self, coordinator: SamsungLocalCoordinator, capability: Capability) -> None:
        super().__init__(coordinator, capability)
        self._attr_device_class = (
            BinarySensorDeviceClass(capability.device_class) if capability.device_class else None
        )
        self._attr_entity_category = (
            EntityCategory(capability.entity_category) if capability.entity_category else None
        )

    @property
    def is_on(self) -> bool | None:
        capability = self.capability
        return bool(capability.value) if capability and capability.value is not None else None
