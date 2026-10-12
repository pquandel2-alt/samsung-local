"""Protocol-neutral models shared by adapters and Home Assistant entities."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any


class Protocol(StrEnum):
    """Supported local protocol families."""

    TIZEN = "tizen"
    OCF = "ocf"
    LEGACY = "legacy"
    SIMULATED = "simulated"


class DeviceCategory(StrEnum):
    """Protocol-neutral device categories."""

    TV = "tv"
    WASHER = "washer"
    DRYER = "dryer"
    DISHWASHER = "dishwasher"
    REFRIGERATOR = "refrigerator"
    AIR_CONDITIONER = "air_conditioner"
    AIR_PURIFIER = "air_purifier"
    APPLIANCE = "appliance"
    UNKNOWN = "unknown"


class ConnectionStatus(StrEnum):
    """Connection status without conflating standby and failure."""

    CONNECTED = "connected"
    STANDBY = "standby"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    AUTHENTICATION_FAILED = "authentication_failed"
    UNAVAILABLE = "unavailable"


class AuthenticationStatus(StrEnum):
    """Authentication state safe to expose in diagnostics."""

    NOT_REQUIRED = "not_required"
    REQUIRED = "required"
    AUTHENTICATED = "authenticated"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


class EntityPlatform(StrEnum):
    """Home Assistant platform selected by the capability engine."""

    MEDIA_PLAYER = "media_player"
    REMOTE = "remote"
    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
    SWITCH = "switch"
    BUTTON = "button"
    SELECT = "select"
    NUMBER = "number"
    CLIMATE = "climate"
    FAN = "fan"


class DataType(StrEnum):
    """Normalized capability value types."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    DURATION = "duration"
    OBJECT = "object"


@dataclass(frozen=True, slots=True)
class DeviceInfo:
    """Stable device identity and descriptive metadata."""

    device_id: str
    name: str
    category: DeviceCategory
    protocol: Protocol
    manufacturer: str = "Samsung"
    model: str | None = None
    firmware: str | None = None
    mac_address: str | None = None
    host: str | None = None
    authentication: AuthenticationStatus = AuthenticationStatus.UNKNOWN


@dataclass(frozen=True, slots=True)
class WriteSpec:
    """A validated protocol write target."""

    command: str
    resource: str | None = None
    field: str | None = None
    payload: Any = None
    requires_remote_control: bool = False
    allowed_states: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Capability:
    """A single entity-shaped function proven by a device response."""

    key: str
    platform: EntityPlatform
    readable: bool = True
    writable: bool = False
    data_type: DataType = DataType.STRING
    value: Any = None
    name: str | None = None
    unit: str | None = None
    device_class: str | None = None
    state_class: str | None = None
    entity_category: str | None = None
    icon: str | None = None
    options: tuple[str, ...] = ()
    native_min: float | None = None
    native_max: float | None = None
    native_step: float | None = None
    write: WriteSpec | None = None
    attributes: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    enabled_default: bool = True

    def with_value(self, value: Any) -> Capability:
        """Return an updated immutable capability."""
        return replace(self, value=value)


@dataclass(frozen=True, slots=True)
class DeviceSnapshot:
    """One confirmed device state, never an optimistic command result."""

    info: DeviceInfo
    connection: ConnectionStatus
    capabilities: Mapping[str, Capability]
    raw: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    unknown_capabilities: tuple[str, ...] = ()
    last_success: datetime | None = None
    error_category: str | None = None
    reconnect_attempt: int = 0

    def capability(self, key: str) -> Capability | None:
        """Return a capability by stable key."""
        return self.capabilities.get(key)


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    """A bounded discovery result safe to show in a config flow."""

    host: str
    protocol: Protocol
    port: int
    name: str
    model: str | None = None
    device_id: str | None = None
    category: DeviceCategory = DeviceCategory.UNKNOWN
    authentication_required: bool = True
    raw: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
