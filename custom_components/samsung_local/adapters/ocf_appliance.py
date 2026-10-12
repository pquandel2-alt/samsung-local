"""Samsung appliance adapter using smartthings-local for OCF over DTLS."""

from __future__ import annotations

import asyncio
import ipaddress
import zlib
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any
from uuid import UUID

import cbor2
from smartthings_local.errors import (
    AuthenticationError as LibraryAuthenticationError,
)
from smartthings_local.errors import (
    SessionError,
    SessionTimeoutError,
)
from smartthings_local.protocol.auth import CertificateAuth, PskAuth
from smartthings_local.protocol.dtls_session import DtlsCoapSession

from ..authentication.manager import OcfCredentialKind, OcfCredentials
from ..capabilities.registry import CapabilityRegistry
from ..capabilities.validation import remote_control_is_enabled, validate_capability_value
from ..exceptions import (
    AuthenticationError,
    CannotConnectError,
    CommandNotSupportedError,
    CommandRejectedError,
    InvalidCommandError,
    RemoteControlDisabledError,
)
from ..models import (
    AuthenticationStatus,
    Capability,
    ConnectionStatus,
    DeviceCategory,
    DeviceInfo,
    DeviceSnapshot,
    Protocol,
)
from .base import SamsungDeviceAdapter

COAP_CONTENT = 0x45
SOURCE_PORT_BASE = 61000


def _path(value: str) -> list[str]:
    return [segment for segment in value.split("/") if segment]


def _is_success(code: int) -> bool:
    return code >> 5 == 2


def _parse_batch(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, list):
        return {}
    resources: dict[str, dict[str, Any]] = {}
    for entry in value:
        if not isinstance(entry, dict):
            continue
        href, representation = entry.get("href"), entry.get("rep")
        if isinstance(href, str) and isinstance(representation, dict):
            resources[href] = representation
    return resources


def _local_source_port(host: str) -> int:
    try:
        offset = int(ipaddress.IPv4Address(host)) & 0xFF
    except ipaddress.AddressValueError:
        offset = zlib.crc32(host.encode()) & 0xFF
    return SOURCE_PORT_BASE + offset


def _device_category(types: tuple[str, ...], model: str, description: str) -> DeviceCategory:
    joined = " ".join((*types, model, description)).lower()
    if "washer" in joined or "_wm_" in joined or "washing" in joined:
        return DeviceCategory.WASHER
    if "dryer" in joined:
        return DeviceCategory.DRYER
    if "dishwasher" in joined:
        return DeviceCategory.DISHWASHER
    if "refriger" in joined or "_ref_" in joined:
        return DeviceCategory.REFRIGERATOR
    if "aircondition" in joined or "_ac_" in joined:
        return DeviceCategory.AIR_CONDITIONER
    if "airpurifier" in joined:
        return DeviceCategory.AIR_PURIFIER
    return DeviceCategory.APPLIANCE


class OcfApplianceAdapter(SamsungDeviceAdapter):
    """Async facade over smartthings-local's deliberately blocking session."""

    def __init__(
        self,
        host: str,
        port: int,
        credentials: OcfCredentials,
        *,
        allow_writes_without_remote: bool = False,
    ) -> None:
        super().__init__()
        self.host = host
        self.port = port
        self.credentials = credentials
        self.allow_writes_without_remote = allow_writes_without_remote
        self._session: DtlsCoapSession | None = None
        self._lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._resources: dict[str, dict[str, Any]] = {}
        self._identity: dict[str, Any] = {}
        self._platform: dict[str, Any] = {}
        self._info: DeviceInfo | None = None
        self._capabilities: dict[str, Capability] = {}
        self._unknown: tuple[str, ...] = ()
        self._registry = CapabilityRegistry()
        self._last_success: datetime | None = None
        self._callback_tasks: set[asyncio.Task[Any]] = set()
        self._observed_resources: set[str] = set()

    def _auth(self) -> CertificateAuth | PskAuth:
        if self.credentials.kind is OcfCredentialKind.CERTIFICATE:
            if not self.credentials.certificate_pem or not self.credentials.private_key_pem:
                raise AuthenticationError("certificate credentials are incomplete")
            return CertificateAuth.from_memory(
                self.credentials.certificate_pem, self.credentials.private_key_pem
            )
        if not self.credentials.psk_identity or not self.credentials.psk_key:
            raise AuthenticationError("PSK credentials are incomplete")
        return PskAuth(
            identity=UUID(self.credentials.psk_identity).bytes,
            key=bytes.fromhex(self.credentials.psk_key),
        )

    async def connect(self) -> None:
        """Open a bounded DTLS session and discover the device."""
        async with self._lock:
            if self._session is not None:
                return
            self._loop = asyncio.get_running_loop()
            try:
                await asyncio.to_thread(self._connect_blocking)
                await asyncio.to_thread(self._refresh_blocking, True)
            except LibraryAuthenticationError as err:
                await asyncio.to_thread(self._close_blocking)
                raise AuthenticationError("the appliance rejected local credentials") from err
            except (SessionError, SessionTimeoutError, OSError, TimeoutError) as err:
                await asyncio.to_thread(self._close_blocking)
                raise CannotConnectError("the appliance did not establish an OCF session") from err

    def _connect_blocking(self) -> None:
        session = DtlsCoapSession(
            self.host,
            self.port,
            auth=self._auth(),
            on_notification=self._notification_from_thread,
            local_port=_local_source_port(self.host),
        )
        session.connect(timeout=10.0)
        session.start_reader()
        self._session = session

    async def disconnect(self) -> None:
        """Close observes and the underlying socket off the event loop."""
        async with self._lock:
            await asyncio.to_thread(self._close_blocking)
        tasks = tuple(self._callback_tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._callback_tasks.clear()

    def _close_blocking(self) -> None:
        session, self._session = self._session, None
        if session is not None:
            session.close()
        self._observed_resources.clear()

    def _live(self) -> DtlsCoapSession:
        if self._session is None:
            raise SessionError("OCF session is not connected")
        return self._session

    def _read(self, href: str, *, query: tuple[str, ...] = ()) -> Any:
        code, payload = self._live().get(_path(href), query=query, timeout=10.0)
        if not _is_success(code):
            return None
        return cbor2.loads(payload) if payload else None

    def _refresh_blocking(self, initial: bool) -> None:
        self._platform = self._read("/oic/p") or self._platform
        self._identity = self._read("/oic/d") or self._identity
        device_batch = self._read("/device/0", query=("if=oic.if.b",))
        resources = _parse_batch(device_batch)
        if not resources:
            device_batch = self._read("/device/0")
            resources = _parse_batch(device_batch)
        if not resources:
            links = self._read("/oic/res")
            if isinstance(links, list):
                # Only read resources the device itself advertised, with a hard bound.
                for link in links[:64]:
                    href = link.get("href") if isinstance(link, dict) else None
                    if not isinstance(href, str) or href.startswith("/oic/"):
                        continue
                    representation = self._read(href)
                    if isinstance(representation, dict):
                        resources[href] = representation
                    self._live().pace()
        else:
            # Resolve batch stubs only at initial discovery; later polls stay light.
            if initial:
                for href, representation in tuple(resources.items()):
                    if set(representation) != {"href"}:
                        continue
                    direct = self._read(href)
                    if isinstance(direct, dict):
                        resources[href] = direct
                    self._live().pace()
        if resources:
            self._resources = resources
        self._update_models()
        if initial:
            for href in (
                "/operational/state/vs/0",
                "/remotectrl/0",
                "/remotectrl/vs/0",
                "/alarms/vs/0",
            ):
                if href in self._resources:
                    try:
                        self._live().subscribe(_path(href))
                    except (SessionError, SessionTimeoutError):
                        # Polling remains the safe fallback.
                        continue
                    self._observed_resources.add(href)

    def _update_models(self) -> None:
        information = self._resources.get("/information/vs/0") or {}
        model = str(
            information.get("x.com.samsung.da.modelNum") or self._platform.get("mnmo") or ""
        ).split("|", 1)[0]
        description = str(information.get("x.com.samsung.da.description") or "")
        types_raw = self._identity.get("rt") or ()
        if isinstance(types_raw, str):
            types_raw = (types_raw,)
        types = tuple(item for item in types_raw if isinstance(item, str))
        category = _device_category(types, model, description)
        device_id = (
            str(
                self._identity.get("di")
                or self._platform.get("pi")
                or information.get("x.com.samsung.da.serialNum")
                or f"ocf-{self.host}"
            )
            .strip()
            .lower()
        )
        if not device_id or device_id.lower().startswith("nothing"):
            device_id = f"ocf-{self.host}"
        firmware = information.get("x.com.samsung.da.firmwareVersion") or information.get(
            "firmwareVersion"
        )
        self._info = DeviceInfo(
            device_id=device_id,
            name=str(self._identity.get("n") or description or f"Samsung {category.value}"),
            category=category,
            protocol=Protocol.OCF,
            manufacturer=str(self._platform.get("mnmn") or "Samsung"),
            model=model or None,
            firmware=str(firmware) if firmware else None,
            host=self.host,
            authentication=AuthenticationStatus.AUTHENTICATED,
        )
        self._capabilities, self._unknown = self._registry.discover(category, self._resources)
        self._last_success = datetime.now(UTC)

    def _notification_from_thread(self, href: str, payload: bytes) -> None:
        try:
            representation = cbor2.loads(payload)
        except (ValueError, TypeError):
            return
        if not isinstance(representation, dict) or self._loop is None:
            return
        self._loop.call_soon_threadsafe(self._apply_notification, href, representation)

    def _apply_notification(self, href: str, representation: dict[str, Any]) -> None:
        self._resources[href] = representation
        self._update_models()
        if self._update_callback is not None:
            result = self._update_callback(self._snapshot())
            if asyncio.iscoroutine(result):
                task = asyncio.create_task(result)
                self._callback_tasks.add(task)
                task.add_done_callback(self._callback_tasks.discard)

    async def get_device_info(self) -> DeviceInfo:
        if self._info is None:
            raise CannotConnectError("device identity is unavailable before connection")
        return self._info

    async def get_capabilities(self) -> dict[str, Capability]:
        return dict(self._capabilities)

    def _snapshot(self) -> DeviceSnapshot:
        if self._info is None:
            raise CannotConnectError("device identity is unavailable")
        return DeviceSnapshot(
            info=self._info,
            connection=ConnectionStatus.CONNECTED,
            capabilities=MappingProxyType(dict(self._capabilities)),
            raw=MappingProxyType(dict(self._resources)),
            unknown_capabilities=self._unknown,
            last_success=self._last_success,
        )

    async def get_state(self) -> DeviceSnapshot:
        async with self._lock:
            try:
                await asyncio.to_thread(self._refresh_blocking, False)
            except (SessionError, SessionTimeoutError, OSError, TimeoutError) as err:
                raise CannotConnectError("OCF state refresh failed") from err
            return self._snapshot()

    async def execute_command(self, command: str, **kwargs: Any) -> None:
        capability = self._capabilities.get(command)
        if capability is None or capability.write is None:
            raise CommandNotSupportedError(f"{command} is not advertised")
        spec = capability.write
        state = self._capabilities.get("machine_state")
        if spec.allowed_states and (state is None or state.value not in spec.allowed_states):
            raise InvalidCommandError(
                f"{command} is not valid while the device is {state.value if state else 'unknown'}"
            )
        if spec.requires_remote_control and not remote_control_is_enabled(self._resources):
            if command in {"start", "pause"} or not self.allow_writes_without_remote:
                raise RemoteControlDisabledError("Smart Control is disabled on the appliance")
        value = kwargs.get("value", spec.payload)
        if spec.payload is None:
            value = validate_capability_value(capability, value)
        if not spec.resource or not spec.field:
            raise CommandNotSupportedError(f"{command} has no validated write target")
        payload: dict[str, Any]
        if spec.command == "ocf_option_write":
            payload = {spec.field: [f"Course_{value}"]}
        elif spec.field == "value":
            payload = {spec.field: bool(value)}
        elif spec.field == "x.com.samsung.da.power":
            payload = {spec.field: "On" if bool(value) else "Off"}
        else:
            payload = {spec.field: value}
        async with self._lock:
            try:
                code, body = await asyncio.to_thread(
                    self._live().post,
                    _path(spec.resource),
                    cbor2.dumps(payload),
                    8.0,
                )
            except (SessionError, SessionTimeoutError, OSError, TimeoutError) as err:
                raise CannotConnectError("command delivery failed") from err
        if not _is_success(code):
            detail = body.decode(errors="replace")[:160] if body else "no detail"
            raise CommandRejectedError(f"device rejected {command}: CoAP {code:#x} ({detail})")

    async def diagnostics(self) -> dict[str, Any]:
        return {
            "transport": "coap_dtls",
            "port": self.port,
            "authentication": self.credentials.kind.value,
            "observe_active": bool(self._observed_resources),
            "observed_resource_count": len(self._observed_resources),
            "resource_count": len(self._resources),
            "unknown_resources": self._unknown,
        }
