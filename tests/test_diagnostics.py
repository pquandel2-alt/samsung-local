"""Diagnostics tests that use Home Assistant's real redaction helper."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from types import MappingProxyType, SimpleNamespace

import homeassistant
import pytest

if getattr(homeassistant, "__file__", None) is None:
    pytest.skip("Home Assistant test harness is not installed", allow_module_level=True)

from custom_components.samsung_local.diagnostics import async_get_config_entry_diagnostics
from custom_components.samsung_local.models import (
    AuthenticationStatus,
    Capability,
    ConnectionStatus,
    DeviceCategory,
    DeviceInfo,
    DeviceSnapshot,
    EntityPlatform,
    Protocol,
)

pytestmark = pytest.mark.homeassistant


class DiagnosticAdapter:
    async def diagnostics(self) -> dict[str, object]:
        return {"token": "adapter-secret", "token_present": True}


class DiagnosticEntry:
    def __init__(self, snapshot: DeviceSnapshot) -> None:
        manager = SimpleNamespace(
            telemetry=SimpleNamespace(reconnect_attempt=2, last_error="timeout"),
            adapter=DiagnosticAdapter(),
        )
        self.runtime_data = SimpleNamespace(data=snapshot, manager=manager)
        self.options = {"debug_diagnostics": True}

    def as_dict(self) -> dict[str, object]:
        return {
            "title": "Private living room",
            "data": {
                "host": "192.0.2.42",
                "token": "entry-secret",
                "device_id": "private-device-id",
            },
        }


async def test_diagnostics_redact_nested_network_and_credentials() -> None:
    info = DeviceInfo(
        "private-device-id",
        "Private living room",
        DeviceCategory.TV,
        Protocol.TIZEN,
        model="Q60C",
        mac_address="00:11:22:33:44:55",
        host="192.0.2.42",
        authentication=AuthenticationStatus.AUTHENTICATED,
    )
    snapshot = DeviceSnapshot(
        info=info,
        connection=ConnectionStatus.CONNECTED,
        capabilities=MappingProxyType(
            {"connection_status": Capability("connection_status", EntityPlatform.SENSOR)}
        ),
        raw=MappingProxyType(
            {
                "/oic/d": {
                    "di": "raw-device-id",
                    "wifiMac": "00:11:22:33:44:55",
                    "name": "Private living room",
                }
            }
        ),
        last_success=datetime.now(UTC),
    )
    result = await async_get_config_entry_diagnostics(
        None,
        DiagnosticEntry(snapshot),  # type: ignore[arg-type]
    )
    serialized = json.dumps(result)
    for secret in (
        "192.0.2.42",
        "entry-secret",
        "adapter-secret",
        "private-device-id",
        "raw-device-id",
        "00:11:22:33:44:55",
        "Private living room",
    ):
        assert secret not in serialized
    assert result["adapter"]["token_present"] is True


async def test_raw_resources_require_explicit_debug_option() -> None:
    snapshot = DeviceSnapshot(
        info=DeviceInfo("safe-id", "Washer", DeviceCategory.WASHER, Protocol.OCF),
        connection=ConnectionStatus.CONNECTED,
        capabilities=MappingProxyType({}),
        raw=MappingProxyType({"/vendor/private": {"value": "private"}}),
    )
    entry = DiagnosticEntry(snapshot)
    entry.options = {}
    result = await async_get_config_entry_diagnostics(
        None,
        entry,  # type: ignore[arg-type]
    )
    assert "raw_resources" not in result
