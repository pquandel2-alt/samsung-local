"""Local Tizen TV adapter backed by samsungtvws."""

from __future__ import annotations

import asyncio
import re
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

from ..apps import (
    AppLaunchMethod,
    AppLaunchResult,
    AppLaunchStatus,
    TvApplication,
    TvAppRegistry,
)
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
from ..power import SamsungTvPowerManager, WakeOnLanConfig
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
    candidate = value.strip().lower()
    if re.fullmatch(r"[0-9a-f]{12}", candidate):
        digits = candidate
    elif re.fullmatch(r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}", candidate):
        digits = candidate.replace(":", "")
    elif re.fullmatch(r"(?:[0-9a-f]{2}-){5}[0-9a-f]{2}", candidate):
        digits = candidate.replace("-", "")
    else:
        return None
    if len(digits) != 12 or set(digits) == {"0"}:
        return None
    return ":".join(digits[index : index + 2] for index in range(0, 12, 2))


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
        wol_broadcast: str = "255.255.255.255",
        wol_port: int = 9,
        power_on_timeout: float = 45.0,
        wol_retries: int = 3,
        configured_apps: list[dict[str, Any]] | None = None,
        configured_device_id: str | None = None,
        configured_name: str | None = None,
        configured_model: str | None = None,
        configured_firmware: str | None = None,
        allow_pairing: bool = False,
        token_callback: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__()
        self.host = host
        self.port = port
        self.token = token
        self.mac_address = _normalize_mac(mac_address)
        self.enable_wol = enable_wol
        self.allow_pairing = allow_pairing
        self._session = session
        self._token_callback = token_callback
        self._remote: SamsungTVWSAsyncRemote | None = None
        self._rest: SamsungTVAsyncRest | None = None
        self._lock = asyncio.Lock()
        self._raw_info: dict[str, Any] = {}
        self._apps: dict[str, str] = {}
        self.app_registry = TvAppRegistry(configured_apps)
        self.power_manager = SamsungTvPowerManager(
            WakeOnLanConfig(
                enabled=enable_wol,
                mac_address=self.mac_address,
                broadcast_address=wol_broadcast,
                port=wol_port,
                timeout=power_on_timeout,
                retries=wol_retries,
            )
        )
        self._app_discovery_attempted = False
        self._info: DeviceInfo | None = (
            DeviceInfo(
                device_id=configured_device_id,
                name=configured_name or "Samsung TV",
                category=DeviceCategory.TV,
                protocol=Protocol.TIZEN,
                model=configured_model,
                firmware=configured_firmware,
                mac_address=self.mac_address,
                host=self.host,
                authentication=(
                    AuthenticationStatus.AUTHENTICATED
                    if token
                    else AuthenticationStatus.NOT_REQUIRED
                    if port == 8001
                    else AuthenticationStatus.REQUIRED
                ),
            )
            if configured_device_id
            else None
        )
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
                device = info.get("device")
                token_auth = (
                    isinstance(device, dict)
                    and str(device.get("TokenAuthSupport", "")).lower() == "true"
                )
                if port == 8002 and token_auth and not self.token and not self.allow_pairing:
                    self._connection = ConnectionStatus.AUTHENTICATION_FAILED
                    raise AuthenticationError(
                        "TV token is missing; interactive reauthentication is required"
                    )
                supplied_token = self.token
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
                self._raw_info = info
                received_token = remote.token or supplied_token
                if port == 8002 and token_auth and not received_token:
                    await remote.close()
                    self._connection = ConnectionStatus.AUTHENTICATION_FAILED
                    raise AuthenticationError("TV pairing completed without a reusable token")
                if (
                    not self.allow_pairing
                    and supplied_token is not None
                    and received_token != supplied_token
                ):
                    await remote.close()
                    self._connection = ConnectionStatus.AUTHENTICATION_FAILED
                    raise AuthenticationError(
                        "TV replaced its stored token; interactive reauthentication is required"
                    )
                self._remote = remote
                self.token = received_token
                if (
                    self.allow_pairing
                    and self.token
                    and self.token != supplied_token
                    and self._token_callback
                ):
                    self._token_callback(self.token)
                self._update_info()
                self._connection = ConnectionStatus.CONNECTED
                self._last_success = datetime.now(UTC)
                installed = None
                if not self._app_discovery_attempted:
                    try:
                        async with asyncio.timeout(6):
                            installed = await remote.app_list()
                    except (
                        ConnectionFailure,
                        ConnectionClosed,
                        WebSocketException,
                        TimeoutError,
                    ):
                        pass
                if installed:
                    self._apps = {
                        str(app["name"]): str(app["appId"])
                        for app in installed
                        if app.get("name") and app.get("appId")
                    }
                    for app_name, app_id in self._apps.items():
                        self.app_registry.add_discovered(app_name, app_id)
                self._app_discovery_attempted = True
                return
            if isinstance(last_error, UnauthorizedError):
                raise AuthenticationError(
                    "TV pairing was denied or its token is invalid"
                ) from last_error
            self._connection = ConnectionStatus.DISCONNECTED
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
        if self.mac_address != self.power_manager.config.mac_address:
            self.power_manager.config = WakeOnLanConfig(
                enabled=self.power_manager.config.enabled,
                mac_address=self.mac_address,
                broadcast_address=self.power_manager.config.broadcast_address,
                port=self.power_manager.config.port,
                timeout=self.power_manager.config.timeout,
                retries=self.power_manager.config.retries,
            )
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

    def _app_sources(self) -> dict[str, str]:
        """Map collision-free source labels to logical app keys."""
        sources: dict[str, str] = {}
        for app in self.app_registry.exposed_apps():
            label = app.name if app.name not in SOURCES else f"App: {app.name}"
            if label in sources:
                label = f"{label} ({app.key})"
            sources[label] = app.key
        return sources

    def _capabilities(self) -> dict[str, Capability]:
        power = self._connection is ConnectionStatus.CONNECTED
        app_sources = self._app_sources()
        capabilities: dict[str, Capability] = {
            "media_player": Capability(
                key="media_player",
                platform=EntityPlatform.MEDIA_PLAYER,
                value="on" if power else "off",
                attributes={
                    "sources": tuple((*SOURCES, *app_sources)),
                    "can_power_on": bool(self.enable_wol and self.mac_address),
                    "can_launch_apps": bool(self.app_registry.all_apps()),
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
        if app_sources:
            capabilities["application"] = Capability(
                key="application",
                platform=EntityPlatform.SELECT,
                value=None,
                writable=True,
                options=tuple(app_sources),
                write=WriteSpec(command="launch_app"),
            )
        return capabilities

    async def get_capabilities(self) -> dict[str, Capability]:
        return self._capabilities()

    def get_fallback_state(self) -> DeviceSnapshot | None:
        """Keep an already configured WOL TV controllable during deep standby."""
        if (
            self._info is None
            or not self.enable_wol
            or self.mac_address is None
            or (self.port == 8002 and not self.token)
        ):
            return None
        self._connection = ConnectionStatus.DISCONNECTED
        return DeviceSnapshot(
            info=self._info,
            connection=ConnectionStatus.DISCONNECTED,
            capabilities=MappingProxyType(self._capabilities()),
            raw=MappingProxyType({}),
            error_category="startup_unreachable",
        )

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

    async def _is_powered_on(self) -> bool:
        """Probe REST without turning a missing endpoint into an off state."""
        if self.port is None:
            return False
        raw = await self._device_info_for_port(self.port)
        if raw is None:
            return False
        self._raw_info = raw
        power_state = str(self._device().get("PowerState", "on")).lower()
        return power_state not in {"standby", "off"}

    async def _connect_after_wake(self) -> None:
        remote = self._remote
        if remote is not None and not remote.is_alive():
            await self.disconnect()
        await self.connect()
        if self._remote is None or not self._remote.is_alive():
            raise CannotConnectError("TV REST endpoint is ready but WebSocket is unavailable")

    async def _async_power_on(self) -> None:
        if not self.power_manager.config.enabled:
            raise CommandNotSupportedError("Wake-on-LAN is not configured for this TV")
        await self.power_manager.async_power_on(self._is_powered_on, self._connect_after_wake)
        self._connection = ConnectionStatus.CONNECTED
        self._last_success = datetime.now(UTC)

    @staticmethod
    def _status_boolean(value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.casefold()
            if normalized in {"true", "yes", "1", "running", "visible"}:
                return True
            if normalized in {"false", "no", "0", "stopped", "hidden"}:
                return False
        return None

    async def _app_status(self, app_id: str) -> tuple[bool, bool | None]:
        """Return (endpoint confirmed, active) without inventing app state."""
        if self._rest is None:
            return False, None
        try:
            response = await self._rest.rest_app_status(app_id)
        except (HttpApiError, ResponseError, TimeoutError, aiohttp.ClientError, OSError):
            return False, None
        if not isinstance(response, dict) or not response:
            return False, None
        active_values = [self._status_boolean(response.get(key)) for key in ("running", "visible")]
        active = True if True in active_values else False if False in active_values else None
        confirmed = any(key in response for key in ("id", "name", "running", "visible", "version"))
        return confirmed, active

    async def _select_app_id(self, app: TvApplication) -> str:
        """Prefer an ID whose local status endpoint confirms installation."""
        for app_id in app.app_ids:
            confirmed, _ = await self._app_status(app_id)
            if confirmed:
                return app_id
        return app.app_ids[0]

    async def _send_app_launch(self, app_id: str, method: AppLaunchMethod) -> tuple[bool, bool]:
        """Send once; return command-sent and immediate device-confirmed flags."""
        if method is AppLaunchMethod.REST:
            if self._rest is None:
                raise CommandNotSupportedError("REST app launch endpoint is unavailable")
            response = await self._rest.rest_app_run(app_id)
            return True, isinstance(response, dict) and bool(response)
        if self._remote is None or not self._remote.is_alive():
            await self.connect()
        assert self._remote is not None
        await self._remote.send_command(ChannelEmitCommand.launch_app(app_id, method.value))
        return True, False

    async def _launch_app(self, value: str, *, turn_on: bool) -> AppLaunchResult:
        """Resolve, wake, launch and verify through one shared code path."""
        app = self.app_registry.resolve(value)
        if not await self._is_powered_on():
            if not turn_on:
                raise CannotConnectError("TV is not ready and automatic power-on was disabled")
            await self._async_power_on()
        else:
            await self._connect_after_wake()

        app_id = await self._select_app_id(app)
        methods = (
            (AppLaunchMethod.DEEP_LINK, AppLaunchMethod.REST)
            if app.method is AppLaunchMethod.AUTO
            else (app.method,)
        )
        last_error: Exception | None = None
        for method in methods:
            try:
                command_sent, device_confirmed = await self._send_app_launch(app_id, method)
            except (
                CommandNotSupportedError,
                ConnectionFailure,
                ConnectionClosed,
                WebSocketException,
                HttpApiError,
                ResponseError,
                TimeoutError,
                aiohttp.ClientError,
                OSError,
            ) as err:
                last_error = err
                continue

            active: bool | None = None
            for _ in range(3):
                await asyncio.sleep(1)
                confirmed, active = await self._app_status(app_id)
                device_confirmed = device_confirmed or confirmed
                if active is True:
                    break
            status = (
                AppLaunchStatus.ACTIVE
                if active is True
                else AppLaunchStatus.DEVICE_CONFIRMED
                if device_confirmed
                else AppLaunchStatus.ACTIVATION_UNVERIFIABLE
            )
            result = AppLaunchResult(
                key=app.key,
                app_id=app_id,
                method=method,
                status=status,
                command_sent=command_sent,
                device_confirmed=device_confirmed,
                active=active,
            )
            self.app_registry.record_launch(app, result, datetime.now(UTC))
            return result
        result = AppLaunchResult(
            key=app.key,
            app_id=app_id,
            method=methods[-1],
            status=AppLaunchStatus.FAILED,
            command_sent=False,
            device_confirmed=False,
            active=None,
        )
        self.app_registry.record_launch(app, result, datetime.now(UTC))
        raise CannotConnectError("all configured local app launch methods failed") from last_error

    async def execute_command(self, command: str, **kwargs: Any) -> None:
        if command == "test_wol":
            if await self._is_powered_on():
                raise InvalidCommandError("turn the TV off before testing Wake-on-LAN")
            await self._async_power_on()
            return
        if command == "power_on":
            await self._async_power_on()
            return
        if command == "select_source":
            source = str(kwargs.get("value", ""))
            app_sources = self._app_sources()
            if source in app_sources:
                await self._launch_app(app_sources[source], turn_on=True)
                return
            elif source in SOURCES:
                await self._send_key(SOURCES[source])
                return
            else:
                raise InvalidCommandError(f"unknown TV source {source!r}")
        if command in {"launch_app", "application"}:
            application = str(kwargs.get("value", ""))
            await self._launch_app(application, turn_on=bool(kwargs.get("turn_on", True)))
            return
        if command == "close_app":
            app_id = str(kwargs.get("value", ""))
            if not app_id or self._rest is None:
                raise CommandNotSupportedError("app close requires a known application id")
            app = self.app_registry.resolve(app_id)
            await self._rest.rest_app_close(app.app_ids[0])
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
            "power": self.power_manager.diagnostics(),
            "apps": self.app_registry.diagnostics(),
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
