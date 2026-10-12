"""Deterministic virtual devices used only as architecture test doubles."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

from custom_components.samsung_local.adapters.base import SamsungDeviceAdapter
from custom_components.samsung_local.exceptions import CannotConnectError, CommandNotSupportedError
from custom_components.samsung_local.models import (
    Capability,
    ConnectionStatus,
    DeviceInfo,
    DeviceSnapshot,
)


class SimulatedSamsungAdapter(SamsungDeviceAdapter):
    def __init__(self, info: DeviceInfo, states: list[dict[str, Capability]]) -> None:
        super().__init__()
        self.info = info
        self.states = states
        self.index = 0
        self.connected = False
        self.connect_failures = 0
        self.commands: list[tuple[str, dict[str, Any]]] = []
        self.command_lock = asyncio.Lock()
        self.active_commands = 0
        self.maximum_parallel_commands = 0

    async def connect(self) -> None:
        if self.connect_failures:
            self.connect_failures -= 1
            raise CannotConnectError("simulated WLAN outage")
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False

    async def get_device_info(self) -> DeviceInfo:
        return self.info

    async def get_capabilities(self) -> dict[str, Capability]:
        return dict(self.states[self.index])

    async def get_state(self) -> DeviceSnapshot:
        if not self.connected:
            raise CannotConnectError("simulated device is disconnected")
        return DeviceSnapshot(
            info=self.info,
            connection=ConnectionStatus.CONNECTED,
            capabilities=MappingProxyType(dict(self.states[self.index])),
            last_success=datetime.now(UTC),
        )

    async def execute_command(self, command: str, **kwargs: Any) -> None:
        if not self.connected:
            raise CannotConnectError("simulated device is disconnected")
        if command not in self.states[self.index]:
            raise CommandNotSupportedError(command)
        self.active_commands += 1
        self.maximum_parallel_commands = max(self.maximum_parallel_commands, self.active_commands)
        try:
            await asyncio.sleep(0)
            self.commands.append((command, kwargs))
        finally:
            self.active_commands -= 1

    def advance(self) -> None:
        self.index = min(self.index + 1, len(self.states) - 1)
