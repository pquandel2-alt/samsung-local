"""Serialize sessions and reconnect without retrying ambiguous writes."""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from typing import Any

from ..adapters.base import SamsungDeviceAdapter
from ..exceptions import CannotConnectError, CommandRejectedError, SamsungLocalError
from ..models import ConnectionStatus, DeviceSnapshot
from .reconnect import BackoffPolicy
from .state import ConnectionTelemetry


class ConnectionManager:
    """One lock and one reconnect schedule per physical device."""

    def __init__(
        self,
        adapter: SamsungDeviceAdapter,
        *,
        backoff: BackoffPolicy | None = None,
        auto_reconnect: bool = True,
    ) -> None:
        self.adapter = adapter
        self.backoff = backoff or BackoffPolicy()
        self.telemetry = ConnectionTelemetry()
        self.auto_reconnect = auto_reconnect
        self._lock = asyncio.Lock()
        self._command_lock = asyncio.Lock()
        self._connected = False
        self._next_retry = 0.0
        self._has_connected = False
        self._app_command_generation = 0

    async def async_connect(self, *, force: bool = False) -> None:
        async with self._lock:
            if self._connected:
                return
            if not force and time.monotonic() < self._next_retry:
                raise CannotConnectError("reconnect is waiting for its bounded backoff")
            self.telemetry.status = ConnectionStatus.CONNECTING
            try:
                await self.adapter.connect()
            except (SamsungLocalError, OSError, TimeoutError) as err:
                self._connected = False
                self.telemetry.status = ConnectionStatus.DISCONNECTED
                self.telemetry.last_error = type(err).__name__
                delay = self.backoff.delay(self.telemetry.reconnect_attempt)
                self.telemetry.reconnect_attempt += 1
                self._next_retry = time.monotonic() + delay
                raise
            self._connected = True
            self._has_connected = True
            self._next_retry = 0.0
            self.telemetry.status = ConnectionStatus.CONNECTED
            self.telemetry.reconnect_attempt = 0
            self.telemetry.last_error = None
            self.telemetry.last_connected = datetime.now(UTC)

    async def async_update(self) -> DeviceSnapshot:
        if not self._connected:
            if self._has_connected and not self.auto_reconnect:
                raise CannotConnectError("automatic reconnect is disabled")
            await self.async_connect()
        try:
            snapshot = await self.adapter.get_state()
        except CannotConnectError:
            await self.async_mark_disconnected()
            raise
        self.telemetry.status = snapshot.connection
        return snapshot

    async def async_execute(self, command: str, **kwargs: Any) -> None:
        bootstraps_connection = command in {"power_on", "test_wol"} or (
            command == "launch_app" and bool(kwargs.get("turn_on", True))
        )
        if not self._connected and not bootstraps_connection:
            await self.async_connect(force=True)
        generation: int | None = None
        if command == "launch_app":
            self._app_command_generation += 1
            generation = self._app_command_generation
        async with self._command_lock:
            if generation is not None and generation != self._app_command_generation:
                raise CommandRejectedError("app launch was superseded by a newer request")
            try:
                # Never automatically retry a write: delivery may have succeeded
                # even when its acknowledgement was lost.
                await self.adapter.execute_command(command, **kwargs)
            except CannotConnectError:
                await self.async_mark_disconnected()
                raise
            if bootstraps_connection:
                self._connected = True
                self._has_connected = True
                self._next_retry = 0.0
                self.telemetry.status = ConnectionStatus.CONNECTED
                self.telemetry.reconnect_attempt = 0
                self.telemetry.last_error = None
                self.telemetry.last_connected = datetime.now(UTC)

    async def async_mark_disconnected(self) -> None:
        async with self._lock:
            self._connected = False
            self.telemetry.status = ConnectionStatus.DISCONNECTED
            self._next_retry = time.monotonic() + self.backoff.delay(
                self.telemetry.reconnect_attempt
            )
            self.telemetry.reconnect_attempt += 1
            await self.adapter.disconnect()

    async def async_disconnect(self) -> None:
        async with self._lock:
            self._connected = False
            self.telemetry.status = ConnectionStatus.DISCONNECTED
            await self.adapter.disconnect()
