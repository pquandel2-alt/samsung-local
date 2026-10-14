from __future__ import annotations

import asyncio

import pytest

from custom_components.samsung_local.connection.manager import ConnectionManager
from custom_components.samsung_local.connection.reconnect import BackoffPolicy
from custom_components.samsung_local.exceptions import CannotConnectError, CommandRejectedError
from custom_components.samsung_local.models import (
    Capability,
    DeviceCategory,
    DeviceInfo,
    EntityPlatform,
    Protocol,
)
from tests.simulated import SimulatedSamsungAdapter


def adapter() -> SimulatedSamsungAdapter:
    return SimulatedSamsungAdapter(
        DeviceInfo("sim-washer", "Virtual Washer", DeviceCategory.WASHER, Protocol.SIMULATED),
        [{"start": Capability("start", EntityPlatform.BUTTON, writable=True)}],
    )


def test_backoff_is_bounded_and_jittered() -> None:
    policy = BackoffPolicy(base=2, maximum=30, jitter=0.2)
    assert policy.delay(0, 0.5) == 2
    assert policy.delay(10, 1.0) == 30
    assert policy.delay(1, 0.0) == pytest.approx(3.2)


async def test_reconnect_after_simulated_wlan_failure(monkeypatch) -> None:
    device = adapter()
    device.connect_failures = 1
    manager = ConnectionManager(device, backoff=BackoffPolicy(base=0, maximum=0, jitter=0))
    with pytest.raises(CannotConnectError):
        await manager.async_update()
    snapshot = await manager.async_update()
    assert snapshot.info.device_id == "sim-washer"
    assert manager.telemetry.reconnect_attempt == 0


async def test_simultaneous_commands_are_serialized() -> None:
    device = adapter()
    manager = ConnectionManager(device)
    await manager.async_connect()
    await asyncio.gather(*(manager.async_execute("start", value=index) for index in range(5)))
    assert [kwargs["value"] for _, kwargs in device.commands] == list(range(5))
    assert device.maximum_parallel_commands == 1


async def test_disabled_auto_reconnect_does_not_reopen_a_lost_session() -> None:
    device = adapter()
    manager = ConnectionManager(device, auto_reconnect=False)
    await manager.async_connect()
    await manager.async_mark_disconnected()

    with pytest.raises(CannotConnectError, match="automatic reconnect is disabled"):
        await manager.async_update()


async def test_newest_app_request_supersedes_an_older_queued_request() -> None:
    device = adapter()
    device.states[0]["launch_app"] = Capability("launch_app", EntityPlatform.BUTTON, writable=True)
    manager = ConnectionManager(device)
    await manager.async_connect()
    first_started = asyncio.Event()
    release_first = asyncio.Event()
    original_execute = device.execute_command

    async def delayed_execute(command: str, **kwargs: object) -> None:
        if command == "launch_app" and not first_started.is_set():
            first_started.set()
            await release_first.wait()
        await original_execute(command, **kwargs)

    device.execute_command = delayed_execute  # type: ignore[method-assign]
    first = asyncio.create_task(manager.async_execute("launch_app", value="first"))
    await first_started.wait()
    stale = asyncio.create_task(manager.async_execute("launch_app", value="stale"))
    await asyncio.sleep(0)
    newest = asyncio.create_task(manager.async_execute("launch_app", value="newest"))
    release_first.set()

    await first
    with pytest.raises(CommandRejectedError, match="superseded"):
        await stale
    await newest
    assert [kwargs["value"] for command, kwargs in device.commands if command == "launch_app"] == [
        "first",
        "newest",
    ]
