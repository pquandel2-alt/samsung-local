"""Serialize sessions and reconnect without retrying ambiguous writes."""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from typing import Any

from ..adapters.base import SamsungDeviceAdapter
from ..exceptions import CannotConnectError, SamsungLocalError
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
    ) -> None:
        self.adapter = adapter
        self.backoff = backoff or BackoffPolicy()
        self.telemetry = ConnectionTelemetry()
        self._lock = asyncio.Lock()
        self._command_lock = asyncio.Lock()
        self._connected = False
        self._next_retry = 0.0

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
            self._next_retry = 0.0
            self.telemetry.status = ConnectionStatus.CONNECTED
            self.telemetry.reconnect_attempt = 0
            self.telemetry.last_error = None
            self.telemetry.last_connected = datetime.now(UTC)

    async def async_update(self) -> DeviceSnapshot:
        if not self._connected:
            await self.async_connect()
        try:
            snapshot = await self.adapter.get_state()
        except CannotConnectError:
            await self.async_mark_disconnected()
            raise
        self.telemetry.status = snapshot.connection
        return snapshot

    async def async_execute(self, command: str, **kwargs: Any) -> None:
        if not self._connected:
            await self.async_connect(force=True)
        async with self._command_lock:
            try:
                # Never automatically retry a write: delivery may have succeeded
                # even when its acknowledgement was lost.
                await self.adapter.execute_command(command, **kwargs)
            except CannotConnectError:
                await self.async_mark_disconnected()
                raise

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
