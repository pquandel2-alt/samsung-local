"""Conservative adapter for Samsung's older HTTPS port-8888 appliances.

This implements the measured TP6X washer envelope.  It deliberately does
not guess mappings for other legacy families.
"""

from __future__ import annotations

import asyncio
import contextlib
import http.client
import json
import os
import ssl
import tempfile
import warnings
from collections.abc import Iterator
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

from ..capabilities.registry import CapabilityRegistry
from ..capabilities.validation import remote_control_is_enabled
from ..exceptions import (
    AuthenticationError,
    CannotConnectError,
    CommandNotSupportedError,
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


@contextlib.contextmanager
def _pem_files(certificate: str, key: str) -> Iterator[list[str]]:
    paths: list[str] = []
    try:
        for content in (certificate, key):
            descriptor, path = tempfile.mkstemp(suffix=".pem")
            paths.append(path)
            with os.fdopen(descriptor, "w") as handle:
                handle.write(content)
            os.chmod(path, 0o600)
        yield paths
    finally:
        for path in paths:
            with contextlib.suppress(OSError):
                os.unlink(path)


def _tls_context(certificate: str, key: str) -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        context.minimum_version = ssl.TLSVersion.TLSv1
    context.set_ciphers("DEFAULT@SECLEVEL=0")
    with _pem_files(certificate, key) as paths:
        context.load_cert_chain(paths[0], paths[1])
    return context


def _prefix(body: dict[str, Any]) -> dict[str, Any]:
    return {f"x.com.samsung.da.{key}": value for key, value in body.items()}


class LegacyApplianceAdapter(SamsungDeviceAdapter):
    """Poll the locally authenticated TP6X HTTPS bridge."""

    def __init__(self, host: str, token: str, certificate: str, key: str, port: int = 8888) -> None:
        super().__init__()
        self.host, self.port, self.token = host, port, token
        self._context = _tls_context(certificate, key)
        self._lock = asyncio.Lock()
        self._resources: dict[str, dict[str, Any]] = {}
        self._info: DeviceInfo | None = None
        self._capabilities: dict[str, Capability] = {}
        self._unknown: tuple[str, ...] = ()
        self._registry = CapabilityRegistry()
        self._last_success: datetime | None = None

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        payload = json.dumps(body).encode() if body is not None else None
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "*/*"}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        connection = http.client.HTTPSConnection(
            self.host, self.port, context=self._context, timeout=8.0
        )
        try:
            connection.request(method, path, body=payload, headers=headers)
            response = connection.getresponse()
            raw = response.read()
        finally:
            connection.close()
        if response.status == 401:
            raise AuthenticationError("the appliance rejected its local token")
        if not 200 <= response.status < 300:
            raise CannotConnectError(f"legacy endpoint returned HTTP {response.status}")
        return json.loads(raw) if raw else None

    def _refresh(self) -> None:
        aggregate = self._request("GET", "/devices/0")
        if not isinstance(aggregate, dict):
            raise CannotConnectError("legacy endpoint returned no device document")
        device = aggregate.get("Device", aggregate)
        if not isinstance(device, dict):
            raise CannotConnectError("legacy device document is malformed")
        for endpoint in ("configuration", "information"):
            try:
                linked = self._request("GET", f"/devices/0/{endpoint}")
            except CannotConnectError:
                continue
            if isinstance(linked, dict):
                device.update(linked.get("Device", linked))
        resources: dict[str, dict[str, Any]] = {}
        operation = device.get("Operation")
        if isinstance(operation, dict):
            resources["/operational/state/vs/0"] = _prefix(operation)
            if "power" in operation:
                resources["/power/vs/0"] = {"x.com.samsung.da.power": operation["power"]}
            if "kidsLock" in operation:
                resources["/kidslock/vs/0"] = {"x.com.samsung.da.kidsLock": operation["kidsLock"]}
        wrappers = {
            "Mode": "/course/vs/0",
            "Washer": "/washer/vs/0",
            "Configuration": "/remotectrl/vs/0",
            "Information": "/information/vs/0",
            "Alarms": "/alarms/vs/0",
        }
        for wrapper, href in wrappers.items():
            value = device.get(wrapper)
            if isinstance(value, dict):
                resources[href] = _prefix(value)
            elif wrapper == "Alarms" and isinstance(value, list):
                resources[href] = {
                    "x.com.samsung.da.items": [
                        _prefix(item) for item in value if isinstance(item, dict)
                    ]
                }
        self._resources = resources
        information = resources.get("/information/vs/0") or {}
        family = str(information.get("x.com.samsung.da.description") or "")
        if family and not family.startswith("TP6X_WASHER"):
            raise CannotConnectError(f"legacy family {family!r} is not mapped safely")
        model = information.get("x.com.samsung.da.modelID") or information.get(
            "x.com.samsung.da.modelNum"
        )
        serial = information.get("x.com.samsung.da.serialNumber") or information.get(
            "x.com.samsung.da.serialNum"
        )
        self._info = DeviceInfo(
            device_id=str(serial or f"legacy-{self.host}").lower(),
            name="Samsung Washer",
            category=DeviceCategory.WASHER,
            protocol=Protocol.LEGACY,
            model=str(model) if model else None,
            host=self.host,
            authentication=AuthenticationStatus.AUTHENTICATED,
        )
        self._capabilities, self._unknown = self._registry.discover(
            DeviceCategory.WASHER, resources
        )
        # Only measured operational writes are retained. Course/settings need
        # staging with start and are not exposed by this conservative adapter.
        self._capabilities = {
            key: capability
            for key, capability in self._capabilities.items()
            if key not in {"program", "temperature", "spin_speed", "rinse_count", "soil_level"}
        }
        self._last_success = datetime.now(UTC)

    async def connect(self) -> None:
        async with self._lock:
            await asyncio.to_thread(self._refresh)

    async def disconnect(self) -> None:
        return None

    async def get_device_info(self) -> DeviceInfo:
        if self._info is None:
            raise CannotConnectError("legacy identity unavailable")
        return self._info

    async def get_capabilities(self) -> dict[str, Capability]:
        return dict(self._capabilities)

    async def get_state(self) -> DeviceSnapshot:
        async with self._lock:
            await asyncio.to_thread(self._refresh)
        assert self._info is not None
        return DeviceSnapshot(
            info=self._info,
            connection=ConnectionStatus.CONNECTED,
            capabilities=MappingProxyType(dict(self._capabilities)),
            raw=MappingProxyType(dict(self._resources)),
            unknown_capabilities=self._unknown,
            last_success=self._last_success,
        )

    async def execute_command(self, command: str, **kwargs: Any) -> None:
        if command not in {"start", "pause", "stop"}:
            raise CommandNotSupportedError(f"legacy command {command!r} is not safely mapped")
        if command != "stop" and not remote_control_is_enabled(self._resources):
            raise RemoteControlDisabledError("Remote Control is disabled on the appliance")
        state = {"start": "Run", "pause": "Pause", "stop": "Ready"}[command]
        async with self._lock:
            await asyncio.to_thread(
                self._request,
                "PUT",
                "/devices/0",
                {"Device": {"Operation": {"state": state}}},
            )

    async def diagnostics(self) -> dict[str, Any]:
        return {
            "transport": "legacy_https_8888",
            "token_present": bool(self.token),
            "mapped_family": "TP6X_WASHER",
            "unknown_resources": self._unknown,
            "security_note": "device-mandated TLS 1.0 is isolated to this adapter",
        }
