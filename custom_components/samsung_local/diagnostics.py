"""Redacted Home Assistant diagnostics."""

from __future__ import annotations

import ipaddress
import re
from datetime import datetime
from enum import Enum
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import SamsungLocalConfigEntry
from .const import CONF_DEBUG_DIAGNOSTICS, SENSITIVE_KEYS

EXTRA_SENSITIVE_KEYS = SENSITIVE_KEYS | {
    "name",
    "title",
    "n",
    "serialNum",
    "serialNumber",
    "serialNo",
    "ip",
    "ipv4",
    "ipv6",
    "address",
    "macAddress",
    "macaddressWiFi",
    "otnDUID",
    "networkId",
    "certificate_pem",
    "private_key_pem",
    "psk_identity",
    "psk_key",
}

MAC_PATTERN = re.compile(r"(?i)(?:[0-9a-f]{2}[:-]){5}[0-9a-f]{2}")
EMAIL_PATTERN = re.compile(r"(?i)\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
IPV4_PATTERN = re.compile(r"(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])")


def _json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item) for item in value]
    return value


def _redact_sensitive_values(value: Any) -> Any:
    """Redact network identifiers even when firmware uses an unknown key."""
    if isinstance(value, dict):
        return {str(key): _redact_sensitive_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_sensitive_values(item) for item in value]
    if not isinstance(value, str):
        return value
    if MAC_PATTERN.search(value) or EMAIL_PATTERN.search(value):
        return "**REDACTED**"
    for candidate in IPV4_PATTERN.findall(value):
        try:
            ipaddress.ip_address(candidate)
        except ValueError:
            continue
        return "**REDACTED**"
    try:
        ipaddress.ip_address(value.strip("[]"))
    except ValueError:
        return value
    return "**REDACTED**"


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SamsungLocalConfigEntry
) -> dict[str, Any]:
    """Return useful protocol evidence with network and identity data removed."""
    coordinator = entry.runtime_data
    snapshot = coordinator.data
    capabilities = {
        key: {
            "platform": capability.platform.value,
            "readable": capability.readable,
            "writable": capability.writable,
            "data_type": capability.data_type.value,
            "unit": capability.unit,
            "device_class": capability.device_class,
            "options_count": len(capability.options),
            "available": capability.value is not None,
        }
        for key, capability in snapshot.capabilities.items()
    }
    payload = {
        "entry": entry.as_dict(),
        "device": {
            "category": snapshot.info.category.value,
            "protocol": snapshot.info.protocol.value,
            "manufacturer": snapshot.info.manufacturer,
            "model": snapshot.info.model,
            "firmware": snapshot.info.firmware,
            "authentication": snapshot.info.authentication.value,
        },
        "connection": {
            "status": snapshot.connection.value,
            "last_success": snapshot.last_success,
            "error_category": snapshot.error_category,
            "reconnect_attempt": coordinator.manager.telemetry.reconnect_attempt,
            "last_connection_error": coordinator.manager.telemetry.last_error,
        },
        "capabilities": capabilities,
        "unknown_capabilities": snapshot.unknown_capabilities,
        "adapter": await coordinator.manager.adapter.diagnostics(),
    }
    if entry.options.get(CONF_DEBUG_DIAGNOSTICS, False):
        payload["raw_resources"] = snapshot.raw
    return async_redact_data(_redact_sensitive_values(_json_safe(payload)), EXTRA_SENSITIVE_KEYS)
