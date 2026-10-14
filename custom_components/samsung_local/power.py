"""Bounded, confirmed Wake-on-LAN power management for Samsung TVs."""

from __future__ import annotations

import asyncio
import ipaddress
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from wakeonlan import send_magic_packet as wake

from .exceptions import CannotConnectError, InvalidCommandError

PowerProbe = Callable[[], Awaitable[bool]]
ConnectCallback = Callable[[], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class WakeOnLanConfig:
    """Validated settings for one physical television."""

    enabled: bool
    mac_address: str | None
    broadcast_address: str = "255.255.255.255"
    port: int = 9
    timeout: float = 45.0
    retries: int = 3

    def validate(self) -> None:
        if not self.enabled:
            raise InvalidCommandError("Wake-on-LAN is disabled for this TV")
        if self.mac_address is None:
            raise InvalidCommandError("Wake-on-LAN requires a valid device MAC address")
        try:
            address = ipaddress.ip_address(self.broadcast_address)
        except ValueError as err:
            raise InvalidCommandError("Wake-on-LAN broadcast address is invalid") from err
        if address.version != 4:
            raise InvalidCommandError("Wake-on-LAN currently requires an IPv4 destination")
        if not 1 <= self.port <= 65535:
            raise InvalidCommandError("Wake-on-LAN port must be between 1 and 65535")
        if not 10 <= self.timeout <= 180:
            raise InvalidCommandError("power-on timeout must be between 10 and 180 seconds")
        if not 1 <= self.retries <= 5:
            raise InvalidCommandError("Wake-on-LAN retries must be between 1 and 5")


class SamsungTvPowerManager:
    """Send bounded magic packets and confirm that Tizen is ready."""

    def __init__(self, config: WakeOnLanConfig) -> None:
        self.config = config
        self._lock = asyncio.Lock()
        self.last_attempt: datetime | None = None
        self.last_success: datetime | None = None
        self.last_attempt_count = 0
        self.last_error: str | None = None

    async def async_power_on(
        self,
        probe: PowerProbe,
        connect: ConnectCallback,
    ) -> None:
        """Wake the TV and return only after REST and WebSocket confirmation."""
        self.config.validate()
        mac_address = self.config.mac_address
        assert mac_address is not None
        async with self._lock:
            self.last_attempt = datetime.now(UTC)
            self.last_attempt_count = 0
            self.last_error = None
            if await probe():
                await connect()
                self.last_success = datetime.now(UTC)
                return

            loop = asyncio.get_running_loop()
            deadline = loop.time() + self.config.timeout
            for attempt in range(1, self.config.retries + 1):
                self.last_attempt_count = attempt
                try:
                    await asyncio.to_thread(
                        wake,
                        mac_address,
                        ip_address=self.config.broadcast_address,
                        port=self.config.port,
                    )
                except OSError as err:
                    self.last_error = type(err).__name__
                    if attempt == self.config.retries:
                        raise CannotConnectError("Wake-on-LAN packet could not be sent") from err

                attempt_deadline = min(
                    deadline,
                    loop.time()
                    + max(1.0, (deadline - loop.time()) / (self.config.retries - attempt + 1)),
                )
                while loop.time() < attempt_deadline:
                    await asyncio.sleep(min(1.0, max(0.0, attempt_deadline - loop.time())))
                    if await probe():
                        try:
                            await connect()
                        except CannotConnectError:
                            continue
                        self.last_success = datetime.now(UTC)
                        self.last_error = None
                        return

            self.last_error = "power_on_timeout"
            raise CannotConnectError(
                f"TV did not become ready within {self.config.timeout:g} seconds"
            )

    def diagnostics(self) -> dict[str, object]:
        """Return safe configuration and outcome data without network identifiers."""
        return {
            "enabled": self.config.enabled,
            "mac_configured": self.config.mac_address is not None,
            "custom_broadcast": self.config.broadcast_address != "255.255.255.255",
            "port": self.config.port,
            "timeout": self.config.timeout,
            "retries": self.config.retries,
            "last_attempt": self.last_attempt,
            "last_success": self.last_success,
            "last_attempt_count": self.last_attempt_count,
            "last_error": self.last_error,
        }
