from __future__ import annotations

import socket

from custom_components.samsung_local.capabilities.registry import CapabilityRegistry
from custom_components.samsung_local.connection.manager import ConnectionManager
from custom_components.samsung_local.models import (
    Capability,
    DeviceCategory,
    DeviceInfo,
    EntityPlatform,
    Protocol,
)
from tests.simulated import SimulatedSamsungAdapter


async def test_runtime_state_and_commands_do_not_need_wan(monkeypatch) -> None:
    def blocked(*args, **kwargs):
        raise AssertionError("unexpected external socket")

    monkeypatch.setattr(socket, "create_connection", blocked)
    info = DeviceInfo("offline", "Offline Washer", DeviceCategory.WASHER, Protocol.SIMULATED)
    adapter = SimulatedSamsungAdapter(
        info,
        [{"start": Capability("start", EntityPlatform.BUTTON, writable=True)}],
    )
    manager = ConnectionManager(adapter)
    snapshot = await manager.async_update()
    await manager.async_execute("start")
    assert snapshot.info.device_id == "offline"
    assert adapter.commands == [("start", {})]


def test_capability_discovery_performs_no_network_io(monkeypatch) -> None:
    monkeypatch.setattr(
        socket, "socket", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network"))
    )
    capabilities, _ = CapabilityRegistry().discover(
        DeviceCategory.WASHER, {"/power/0": {"value": True}}
    )
    assert capabilities["power"].value is True
