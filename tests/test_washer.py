from __future__ import annotations

from types import MappingProxyType

import pytest

from custom_components.samsung_local.adapters.legacy_appliance import (
    LegacyApplianceAdapter,
)
from custom_components.samsung_local.adapters.ocf_appliance import OcfApplianceAdapter
from custom_components.samsung_local.authentication.certificates import (
    mint_self_signed_client,
)
from custom_components.samsung_local.authentication.manager import (
    OcfCredentialKind,
    OcfCredentials,
)
from custom_components.samsung_local.capabilities.registry import CapabilityRegistry
from custom_components.samsung_local.exceptions import (
    CannotConnectError,
    RemoteControlDisabledError,
)
from custom_components.samsung_local.models import DeviceCategory


class FakeSession:
    def __init__(self) -> None:
        self.posts: list[tuple[list[str], bytes, float]] = []

    def post(self, path: list[str], payload: bytes, timeout: float):
        self.posts.append((path, payload, timeout))
        return 0x44, b""


def adapter_with_resources(resources: dict[str, dict]) -> tuple[OcfApplianceAdapter, FakeSession]:
    adapter = OcfApplianceAdapter(
        "192.0.2.40",
        49154,
        OcfCredentials(
            OcfCredentialKind.PSK,
            psk_identity="11111111-2222-3333-4444-555555555555",
            psk_key="11" * 16,
        ),
    )
    adapter._resources = resources
    adapter._capabilities, adapter._unknown = CapabilityRegistry().discover(
        DeviceCategory.WASHER, resources
    )
    session = FakeSession()
    adapter._session = session  # type: ignore[assignment]
    return adapter, session


async def test_start_requires_explicit_smart_control() -> None:
    adapter, session = adapter_with_resources(
        {"/operational/state/vs/0": {"x.com.samsung.da.state": "Ready"}}
    )
    with pytest.raises(RemoteControlDisabledError):
        await adapter.execute_command("start")
    assert not session.posts


async def test_safety_override_never_bypasses_start_gate() -> None:
    adapter, session = adapter_with_resources(
        {"/operational/state/vs/0": {"x.com.samsung.da.state": "Ready"}}
    )
    adapter.allow_writes_without_remote = True
    with pytest.raises(RemoteControlDisabledError):
        await adapter.execute_command("start")
    assert not session.posts


async def test_start_posts_real_ocf_command_when_allowed() -> None:
    adapter, session = adapter_with_resources(
        {
            "/operational/state/vs/0": {"x.com.samsung.da.state": "Ready"},
            "/remotectrl/0": {"value": True},
        }
    )
    await adapter.execute_command("start")
    assert session.posts[0][0] == ["operational", "state", "vs", "0"]


def test_device_snapshot_mappings_are_immutable() -> None:
    resources = MappingProxyType({"/power/0": {"value": True}})
    with pytest.raises(TypeError):
        resources["/power/0"] = {}  # type: ignore[index]


def legacy_adapter(monkeypatch, *, family: str = "TP6X_WASHER"):
    certificate, key = mint_self_signed_client("11111111-2222-3333-4444-555555555555")
    adapter = LegacyApplianceAdapter("192.0.2.90", "local-token", certificate, key)
    requests: list[tuple[str, str, dict | None]] = []

    def request(method: str, path: str, body: dict | None = None):
        requests.append((method, path, body))
        if path == "/devices/0":
            if method == "PUT":
                return {}
            return {
                "Device": {
                    "Operation": {
                        "state": "Ready",
                        "remainingTime": "00:42:00",
                        "progress": "None",
                    },
                    "Configuration": {"remoteControlEnabled": True},
                    "Information": {
                        "description": family,
                        "modelID": "WW90TEST",
                        "serialNumber": "anonymized-serial",
                    },
                }
            }
        return {"Device": {}}

    monkeypatch.setattr(adapter, "_request", request)
    return adapter, requests


async def test_legacy_tp6x_profile_reads_and_executes_measured_write(monkeypatch) -> None:
    adapter, requests = legacy_adapter(monkeypatch)
    await adapter.connect()
    info = await adapter.get_device_info()
    capabilities = await adapter.get_capabilities()
    assert info.model == "WW90TEST"
    assert capabilities["machine_state"].value == "idle"
    assert "program" not in capabilities

    await adapter.execute_command("start")
    assert requests[-1] == (
        "PUT",
        "/devices/0",
        {"Device": {"Operation": {"state": "Run"}}},
    )


async def test_legacy_unknown_family_is_rejected(monkeypatch) -> None:
    adapter, _ = legacy_adapter(monkeypatch, family="UNKNOWN_APPLIANCE")
    with pytest.raises(CannotConnectError, match="not mapped safely"):
        await adapter.connect()
