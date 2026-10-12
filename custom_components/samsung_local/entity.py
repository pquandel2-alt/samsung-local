"""Shared Samsung Local coordinator entity."""

from __future__ import annotations

from typing import Any

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo as HADeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SamsungLocalCoordinator
from .exceptions import SamsungLocalError
from .models import Capability, ConnectionStatus


class SamsungLocalEntity(CoordinatorEntity[SamsungLocalCoordinator]):
    """An entity whose value always comes from a confirmed snapshot."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SamsungLocalCoordinator, capability: Capability) -> None:
        super().__init__(coordinator)
        self.capability_key = capability.key
        info = coordinator.data.info
        self._attr_unique_id = f"{info.device_id}_{capability.key}"
        self._attr_translation_key = capability.key
        self._attr_icon = capability.icon
        self._attr_entity_registry_enabled_default = capability.enabled_default
        device_info = HADeviceInfo(
            identifiers={(DOMAIN, info.device_id)},
            manufacturer=info.manufacturer,
            name=info.name,
            model=info.model,
            sw_version=info.firmware,
        )
        if info.mac_address:
            device_info["connections"] = {(dr.CONNECTION_NETWORK_MAC, info.mac_address)}
        self._attr_device_info = device_info

    @property
    def capability(self) -> Capability | None:
        return self.coordinator.data.capability(self.capability_key)

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.capability is not None
            and self.coordinator.data.connection
            not in {ConnectionStatus.DISCONNECTED, ConnectionStatus.UNAVAILABLE}
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        capability = self.capability
        return dict(capability.attributes) if capability and capability.attributes else None

    async def _async_command(self, command: str, **kwargs: Any) -> None:
        try:
            await self.coordinator.async_command(command, **kwargs)
        except SamsungLocalError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={"error": str(err)},
            ) from err
