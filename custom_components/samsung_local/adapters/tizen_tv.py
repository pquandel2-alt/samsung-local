"""Local Tizen TV adapter backed by samsungtvws."""

from __future__ import annotations

import asyncio
import socket
from collections.abc import Callable
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

import aiohttp
from samsungtvws.async_remote import SamsungTVWSAsyncRemote
from samsungtvws.async_rest import SamsungTVAsyncRest
from samsungtvws.exceptions import (
    ConnectionFailure,
    HttpApiError,
    ResponseError,
    UnauthorizedError,
)
from samsungtvws.remote import ChannelEmitCommand, SendRemoteKey
from websockets.exceptions import ConnectionClosed, WebSocketException

from ..const import PAIRING_TIMEOUT, REQUEST_TIMEOUT, TIZEN_PORTS
from ..exceptions import (
    AuthenticationError,
    CannotConnectError,
    CommandNotSupportedError,
    InvalidCommandError,
)
from ..models import (
    AuthenticationStatus,
    Capability,
    ConnectionStatus,
    DataType,
    DeviceCategory,
    DeviceInfo,
    DeviceSnapshot,
    EntityPlatform,
    Protocol,
    WriteSpec,
)
from .base import SamsungDeviceAdapter

TV_KEYS: dict[str, str] = {
    "power_off": "KEY_POWER",
    "volume_up": "KEY_VOLUP",
    "volume_down": "KEY_VOLDOWN",
    "mute": "KEY_MUTE",
    "home": "KEY_HOME",
    "back": "KEY_RETURN",
    "up": "KEY_UP",
    "down": "KEY_DOWN",
    "left": "KEY_LEFT",
    "right": "KEY_RIGHT",
    "enter": "KEY_ENTER",
    "play": "KEY_PLAY",
    "pause": "KEY_PAUSE",
    "stop": "KEY_STOP",
    "channel_up": "KEY_CHUP",
    "channel_down": "KEY_CHDOWN",
}

SOURCES: dict[str, str] = {
    "TV": "KEY_TV",
    "HDMI": "KEY_HDMI",
    "HDMI 1": "KEY_HDMI1",
    "HDMI 2": "KEY_HDMI2",
    "HDMI 3": "KEY_HDMI3",
    "HDMI 4": "KEY_HDMI4",
}


def _normalize_mac(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    digits = "".join(character for character in value.lower() if character in "0123456789abcdef")
    if len(digits) != 12 or set(digits) == {"0"}:
        return None
    return ":".join(digits[index : index + 2] for index in range(0, 12, 2))


def _wake(mac: str) -> None:
    packet = bytes.fromhex("ff" * 6 + mac.replace(":", "") * 16)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as wol_socket:
        wol_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        wol_socket.sendto(packet, ("255.255.255.255", 9))


class TizenTvAdapter(SamsungDeviceAdapter):
    """Modern Samsung TV WebSocket/REST adapter."""

    def __init__(
        self,
        host: str,
        session: aiohttp.ClientSession,
        *,
        port: int | None = None,
        token: str | None = None,
        mac_address: str | None = None,
        enable_wol: bool = False,
        token_callback: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__()
        self.host = host
        self.port = port
        self.token = token
        self.mac_address = _normalize_mac(mac_address)
        self.enable_wol = enable_wol
        self._session = session
        self._token_callback = token_callback
        self._remote: SamsungTVWSAsyncRemote | None = None
        self._rest: SamsungTVAsyncRest | None = None
        self._lock = asyncio.Lock()
        self._raw_info: dict[str, Any] = {}
        self._apps: dict[str, str] = {}
        self._info: DeviceInfo | None = None
        self._connection = ConnectionStatus.DISCONNECTED
        self._last_success: datetime | None = None

    async def _device_info_for_port(self, port: int) -> dict[str, Any] | None:
        rest = SamsungTVAsyncRest(
            self.host, session=self._session, port=port, timeout=REQUEST_TIMEOUT
        )
        try:
            result = await rest.rest_device_info()
        except (HttpApiError, ResponseError, TimeoutError, aiohttp.ClientError, OSError):
            return None
        self._rest = rest
        return result

    async def connect(self) -> None:
        async with self._lock:
            if self._remote is not None and self._remote.is_alive():
                return
            self._connection = ConnectionStatus.CONNECTING
            ports = (self.port,) if self.port else TIZEN_PORTS
            last_error: Exception | None = None
            for port in ports:
                info = await self._device_info_for_port(port)
                if info is None:
                    continue
                remote = SamsungTVWSAsyncRemote(
                    host=self.host,
                    port=port,
                    token=self.token,
                    timeout=PAIRING_TIMEOUT,
                    name="Samsung Local",
                    key_press_delay=0.25,
                )
                try:
                    await remote.start_listening(self._remote_event)
                except UnauthorizedError as err:
                    last_error = err
                    await remote.close()
                    self._connection = ConnectionStatus.AUTHENTICATION_FAILED
                    break
                except (
                    ConnectionFailure,
                    ConnectionClosed,
                    WebSocketException,
                    TimeoutError,
                    OSError,
                ) as err:
                    last_error = err
                    await remote.close()
                    continue
                self.port = port
                self._remote = remote
                self._raw_info = info
                self.token = remote.token or self.token
                if self.token and self._token_callback:
                    self._token_callback(self.token)
                self._update_info()
                self._connection = ConnectionStatus.CONNECTED
                self._last_success = datetime.now(UTC)
                try:
                    installed = await remote.app_list()
                except (
                    ConnectionFailure,
                    ConnectionClosed,
                    WebSocketException,
                    TimeoutError,
                ):
                    installed = None
                if installed:
                    self._apps = {
                        str(app["name"]): str(app["appId"])
                        for app in installed
                        if app.get("name") and app.get("appId")
                    }
                return
            if isinstance(last_error, UnauthorizedError):
                raise AuthenticationError(
                    "TV pairing was denied or its token is invalid"
                ) from last_error
            raise CannotConnectError("no supported Tizen endpoint responded") from last_error

    async def disconnect(self) -> None:
        async with self._lock:
            remote, self._remote = self._remote, None
            if remote is not None:
                try:
                    await remote.close()
                except (OSError, WebSocketException):
                    pass
            self._connection = ConnectionStatus.DISCONNECTED

    def _device(self) -> dict[str, Any]:
        device = self._raw_info.get("device")
        return device if isinstance(device, dict) else {}

    def _update_info(self) -> None:
        device = self._device()
        self.mac_address = _normalize_mac(device.get("wifiMac")) or self.mac_address
        device_id = str(
            device.get("id") or self._raw_info.get("id") or self.mac_address or f"tv-{self.host}"
        )
        firmware = device.get("firmwareVersion") or device.get("version")
        self._info = DeviceInfo(
            device_id=device_id.lower(),
            name=str(device.get("name") or self._raw_info.get("name") or "Samsung TV"),
            category=DeviceCategory.TV,
            protocol=Protocol.TIZEN,
            model=str(device.get("modelName")) if device.get("modelName") else None,
            firmware=str(firmware) if firmware else None,
            mac_address=self.mac_address,
            host=self.host,
            authentication=AuthenticationStatus.AUTHENTICATED,
        )

    async def _remote_event(self, event: str, response: Any) -> None:
        # samsungtvws handles tokens and app-list futures internally.  Keep
        # opaque events out of state and diagnostics because they may contain
        # device identifiers.
        return None

    async def get_device_info(self) -> DeviceInfo:
        if self._info is None:
            raise CannotConnectError("TV identity is unavailable before pairing")
        return self._info

    def _capabilities(self) -> dict[str, Capability]:
        power = self._connection is ConnectionStatus.CONNECTED
        capabilities: dict[str, Capability] = {
            "media_player": Capability(
                key="media_player",
                platform=EntityPlatform.MEDIA_PLAYER,
                value="on" if power else "off",
                attributes={
                    "sources": tuple((*SOURCES, *self._apps)),
                    "can_power_on": bool(self.enable_wol and self.mac_address),
                    "can_launch_apps": bool(self._apps),
                },
            ),
            "remote": Capability(
                key="remote",
                platform=EntityPlatform.REMOTE,
                value=power,
                data_type=DataType.BOOLEAN,
                writable=True,
                write=WriteSpec(command="remote_key"),
            ),
            "connection_status": Capability(
                key="connection_status",
                platform=EntityPlatform.SENSOR,
                value=self._connection.value,
                device_class="enum",
                options=tuple(status.value for status in ConnectionStatus),
                entity_category="diagnostic",
            ),
        }
        if self._apps:
            capabilities["application"] = Capability(
                key="application",
                platform=EntityPlatform.SELECT,
                value=None,
                writable=True,
                options=tuple(self._apps),
                write=WriteSpec(command="launch_app"),
            )
        return capabilities

    async def get_capabilities(self) -> dict[str, Capability]:
        return self._capabilities()

    async def get_state(self) -> DeviceSnapshot:
        if self.port is None:
            raise CannotConnectError("TV endpoint is unknown")
        raw = await self._device_info_for_port(self.port)
        if raw is None:
            # A failed WebSocket/REST request is not proof of standby.
            self._connection = ConnectionStatus.DISCONNECTED
        else:
            self._raw_info = raw
            power_state = str(self._device().get("PowerState", "on")).lower()
            self._connection = (
                ConnectionStatus.STANDBY
                if power_state in {"standby", "off"}
                else ConnectionStatus.CONNECTED
            )
            self._last_success = datetime.now(UTC)
            self._update_info()
        if self._info is None:
            raise CannotConnectError("TV identity is unavailable")
        return DeviceSnapshot(
            info=self._info,
            connection=self._connection,
            capabilities=MappingProxyType(self._capabilities()),
            raw=MappingProxyType({"device": dict(self._device())}),
            last_success=self._last_success,
        )

    async def _send_key(self, key: str) -> None:
        if self._remote is None or not self._remote.is_alive():
            await self.connect()
        assert self._remote is not None
        try:
            await self._remote.send_command(SendRemoteKey.click(key), key_press_delay=0.25)
        except (ConnectionFailure, ConnectionClosed, WebSocketException, OSError) as err:
            await self.disconnect()
            raise CannotConnectError("TV command connection failed") from err

    async def execute_command(self, command: str, **kwargs: Any) -> None:
        if command == "power_on":
            if not self.enable_wol or not self.mac_address:
                raise CommandNotSupportedError("Wake-on-LAN is not configured with a valid MAC")
            await asyncio.to_thread(_wake, self.mac_address)
            return
        if command == "select_source":
            source = str(kwargs.get("value", ""))
            if source in self._apps:
                command, kwargs = "launch_app", {"value": source}
            elif source in SOURCES:
                await self._send_key(SOURCES[source])
                return
            else:
                raise InvalidCommandError(f"unknown TV source {source!r}")
        if command == "launch_app":
            application = str(kwargs.get("value", ""))
            known_ids = set(self._apps.values())
            if application not in self._apps and application not in known_ids:
                raise InvalidCommandError("the TV did not advertise this application")
            app_id = self._apps.get(application, application)
            if self._remote is None or not self._remote.is_alive():
                await self.connect()
            assert self._remote is not None
            await self._remote.send_command(ChannelEmitCommand.launch_app(app_id))
            return
        if command == "close_app":
            app_id = str(kwargs.get("value", ""))
            if not app_id or self._rest is None:
                raise CommandNotSupportedError("app close requires a known application id")
            await self._rest.rest_app_close(self._apps.get(app_id, app_id))
            return
        if command == "remote_key":
            key = str(kwargs.get("value", ""))
            if not key.startswith("KEY_") or len(key) > 64:
                raise InvalidCommandError("remote keys must be Samsung KEY_* identifiers")
            await self._send_key(key)
            return
        mapped_key = TV_KEYS.get(command)
        if mapped_key is None:
            raise CommandNotSupportedError(f"unknown TV command {command!r}")
        await self._send_key(mapped_key)

    async def diagnostics(self) -> dict[str, Any]:
        device = self._device()
        return {
            "transport": "tizen_websocket",
            "port": self.port,
            "token_present": bool(self.token),
            "connection": self._connection.value,
            "app_count": len(self._apps),
            "device_features": {
                key: value
                for key, value in device.items()
                if key
                in {
                    "FrameTVSupport",
                    "GamePadSupport",
                    "ImeSyncedSupport",
                    "PowerState",
                    "TokenAuthSupport",
                    "VoiceSupport",
                }
            },
        }
