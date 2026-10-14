"""Common asynchronous device-adapter contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any

from ..models import Capability, DeviceInfo, DeviceSnapshot

UpdateCallback = Callable[[DeviceSnapshot], Awaitable[None] | None]


class SamsungDeviceAdapter(ABC):
    """Keep protocol mechanics outside Home Assistant entities."""

    def __init__(self) -> None:
        self._update_callback: UpdateCallback | None = None

    def set_update_callback(self, callback: UpdateCallback | None) -> None:
        """Set the callback used for protocol push notifications."""
        self._update_callback = callback

    @abstractmethod
    async def connect(self) -> None:
        """Open and authenticate a local connection."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Release all local resources."""

    @abstractmethod
    async def get_device_info(self) -> DeviceInfo:
        """Return stable identity learned from the device."""

    @abstractmethod
    async def get_capabilities(self) -> dict[str, Capability]:
        """Discover only functions evidenced by the endpoint."""

    @abstractmethod
    async def get_state(self) -> DeviceSnapshot:
        """Fetch a confirmed state snapshot."""

    @abstractmethod
    async def execute_command(self, command: str, **kwargs: Any) -> None:
        """Execute one validated local command."""

    def get_fallback_state(self) -> DeviceSnapshot | None:
        """Return a safe startup snapshot, or none when live setup is mandatory."""
        return None

    async def diagnostics(self) -> dict[str, Any]:
        """Return protocol diagnostics without credentials."""
        return {}
