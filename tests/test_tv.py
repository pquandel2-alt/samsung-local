from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar
from unittest.mock import AsyncMock

import pytest

from custom_components.samsung_local.adapters.tizen_tv import (
    TizenTvAdapter,
    _normalize_mac,
)
from custom_components.samsung_local.apps import AppLaunchStatus
from custom_components.samsung_local.exceptions import (
    AuthenticationError,
    CannotConnectError,
    CommandNotSupportedError,
    InvalidCommandError,
)
from custom_components.samsung_local.models import ConnectionStatus


def test_tv_profiles_do_not_infer_model_from_firmware() -> None:
    fixture = json.loads((Path(__file__).parent / "fixtures" / "tv_8_series_43.json").read_text())
    assert fixture["device"]["modelName"] != fixture["device"]["firmwareVersion"]


def test_mac_normalization_rejects_placeholder() -> None:
    assert _normalize_mac("02-00-00-00-00-01") == "02:00:00:00:00:01"
    assert _normalize_mac("020000000001") == "02:00:00:00:00:01"
    assert _normalize_mac("00:00:00:00:00:00") is None
    assert _normalize_mac("prefix-02:00:00:00:00:01") is None


class FakeRemote:
    instances: ClassVar[list[FakeRemote]] = []

    def __init__(self, **kwargs) -> None:
        self.token = kwargs.get("token") or "paired-token"
        self.alive = False
        self.commands: list[object] = []
        self.closed = False
        self.__class__.instances.append(self)

    def is_alive(self) -> bool:
        return self.alive

    async def start_listening(self, callback) -> None:
        self.alive = True

    async def app_list(self):
        return [{"name": "Netflix", "appId": "11101200001"}]

    async def send_command(self, command, key_press_delay=None) -> None:
        self.commands.append(command)

    async def close(self) -> None:
        self.closed = True
        self.alive = False


async def test_tizen_pairing_state_apps_and_cleanup(monkeypatch) -> None:
    FakeRemote.instances.clear()
    monkeypatch.setattr(
        "custom_components.samsung_local.adapters.tizen_tv.asyncio.sleep", AsyncMock()
    )
    monkeypatch.setattr(
        "custom_components.samsung_local.adapters.tizen_tv.SamsungTVWSAsyncRemote",
        FakeRemote,
    )
    tokens: list[str] = []
    adapter = TizenTvAdapter(
        "192.0.2.80",
        object(),  # type: ignore[arg-type]
        port=8002,
        allow_pairing=True,
        token_callback=tokens.append,
    )
    on_payload = {
        "device": {
            "id": "stable-tv-id",
            "name": "Q60C",
            "modelName": "GQ55Q60CAUXZG",
            "firmwareVersion": "T-KSU2EDEUC",
            "wifiMac": "02:00:00:00:00:80",
            "PowerState": "on",
        }
    }
    adapter._device_info_for_port = AsyncMock(return_value=on_payload)

    await adapter.connect()
    assert tokens == ["paired-token"]
    assert (await adapter.get_device_info()).model == "GQ55Q60CAUXZG"
    capabilities = await adapter.get_capabilities()
    assert capabilities["application"].options == ("Netflix",)
    assert "Netflix" in capabilities["media_player"].attributes["sources"]

    await adapter.execute_command("launch_app", value="Netflix")
    assert len(FakeRemote.instances[0].commands) == 1
    await adapter.execute_command("select_source", value="Netflix")
    await adapter.execute_command("application", value="Netflix")
    assert len(FakeRemote.instances[0].commands) == 3
    with pytest.raises(InvalidCommandError):
        await adapter.execute_command("launch_app", value="Unadvertised app")
    with pytest.raises(InvalidCommandError):
        await adapter.execute_command("remote_key", value="POWER")
    with pytest.raises(CommandNotSupportedError):
        await adapter.execute_command("power_on")

    standby_payload = {"device": {**on_payload["device"], "PowerState": "standby"}}
    adapter._device_info_for_port = AsyncMock(return_value=standby_payload)
    snapshot = await adapter.get_state()
    assert snapshot.connection is ConnectionStatus.STANDBY

    await adapter.disconnect()
    assert FakeRemote.instances[0].closed


async def test_app_launch_wakes_tv_and_uses_one_shared_launch_path(monkeypatch) -> None:
    """An app request wakes first and reports only observable confirmation."""
    adapter = TizenTvAdapter(
        "192.0.2.83",
        object(),  # type: ignore[arg-type]
        port=8002,
        token="stored-token",
        mac_address="02:00:00:00:00:83",
        enable_wol=True,
    )
    powered = AsyncMock(return_value=False)
    wake = AsyncMock()
    launch = AsyncMock(return_value=(True, False))
    status = AsyncMock(return_value=(False, None))
    monkeypatch.setattr(adapter, "_is_powered_on", powered)
    monkeypatch.setattr(adapter, "_async_power_on", wake)
    monkeypatch.setattr(adapter, "_send_app_launch", launch)
    monkeypatch.setattr(adapter, "_app_status", status)
    monkeypatch.setattr(
        "custom_components.samsung_local.adapters.tizen_tv.asyncio.sleep", AsyncMock()
    )

    result = await adapter._launch_app("netflix", turn_on=True)

    wake.assert_awaited_once()
    launch.assert_awaited_once()
    assert result.status is AppLaunchStatus.ACTIVATION_UNVERIFIABLE
    assert result.command_sent is True
    assert result.active is None


async def test_app_launch_can_require_an_already_powered_tv(monkeypatch) -> None:
    adapter = TizenTvAdapter(
        "192.0.2.84",
        object(),  # type: ignore[arg-type]
        configured_apps=[
            {
                "key": "custom",
                "name": "Custom App",
                "app_ids": ["org.example.custom"],
                "method": "NATIVE_LAUNCH",
            }
        ],
    )
    monkeypatch.setattr(adapter, "_is_powered_on", AsyncMock(return_value=False))

    with pytest.raises(CannotConnectError, match="automatic power-on was disabled"):
        await adapter._launch_app("custom", turn_on=False)


async def test_auto_app_method_falls_back_only_after_transport_rejection(monkeypatch) -> None:
    adapter = TizenTvAdapter("192.0.2.86", object())  # type: ignore[arg-type]
    monkeypatch.setattr(adapter, "_is_powered_on", AsyncMock(return_value=True))
    monkeypatch.setattr(adapter, "_connect_after_wake", AsyncMock())
    launch = AsyncMock(
        side_effect=[CommandNotSupportedError("deep link unavailable"), (True, True)]
    )
    monkeypatch.setattr(adapter, "_send_app_launch", launch)
    monkeypatch.setattr(adapter, "_app_status", AsyncMock(return_value=(True, None)))
    monkeypatch.setattr(
        "custom_components.samsung_local.adapters.tizen_tv.asyncio.sleep", AsyncMock()
    )

    result = await adapter._launch_app("prime video", turn_on=True)

    assert launch.await_count == 2
    assert result.method.value == "REST"
    assert result.status is AppLaunchStatus.DEVICE_CONFIRMED


async def test_power_on_delegates_to_confirming_power_manager(monkeypatch) -> None:
    adapter = TizenTvAdapter(
        "192.0.2.85",
        object(),  # type: ignore[arg-type]
        mac_address="02:00:00:00:00:85",
        enable_wol=True,
    )
    confirmed_wake = AsyncMock()
    monkeypatch.setattr(adapter.power_manager, "async_power_on", confirmed_wake)

    await adapter.execute_command("power_on")

    confirmed_wake.assert_awaited_once_with(adapter._is_powered_on, adapter._connect_after_wake)
    assert adapter._connection is ConnectionStatus.CONNECTED


async def test_wol_test_refuses_to_pass_while_tv_is_already_on(monkeypatch) -> None:
    adapter = TizenTvAdapter(
        "192.0.2.87",
        object(),  # type: ignore[arg-type]
        mac_address="02:00:00:00:00:87",
        enable_wol=True,
    )
    monkeypatch.setattr(adapter, "_is_powered_on", AsyncMock(return_value=True))
    wake = AsyncMock()
    monkeypatch.setattr(adapter, "_async_power_on", wake)

    with pytest.raises(InvalidCommandError, match="turn the TV off"):
        await adapter.execute_command("test_wol")
    wake.assert_not_awaited()


async def test_runtime_never_starts_pairing_without_stored_token(monkeypatch) -> None:
    """A background refresh must not cause a consent prompt on the TV."""
    FakeRemote.instances.clear()
    monkeypatch.setattr(
        "custom_components.samsung_local.adapters.tizen_tv.SamsungTVWSAsyncRemote",
        FakeRemote,
    )
    adapter = TizenTvAdapter("192.0.2.81", object(), port=8002)  # type: ignore[arg-type]
    adapter._device_info_for_port = AsyncMock(  # type: ignore[method-assign]
        return_value={"device": {"TokenAuthSupport": "true"}}
    )

    with pytest.raises(AuthenticationError, match="token is missing"):
        await adapter.connect()

    assert FakeRemote.instances == []
    assert adapter._connection is ConnectionStatus.AUTHENTICATION_FAILED


async def test_runtime_rejects_unexpected_token_replacement(monkeypatch) -> None:
    """A reconnect cannot silently turn into recurring interactive pairing."""

    class ReplacingRemote(FakeRemote):
        def __init__(self, **kwargs) -> None:
            super().__init__(**kwargs)
            self.token = "replacement-token"

    ReplacingRemote.instances.clear()
    monkeypatch.setattr(
        "custom_components.samsung_local.adapters.tizen_tv.SamsungTVWSAsyncRemote",
        ReplacingRemote,
    )
    saved: list[str] = []
    adapter = TizenTvAdapter(
        "192.0.2.82",
        object(),  # type: ignore[arg-type]
        port=8002,
        token="stored-token",
        token_callback=saved.append,
    )
    adapter._device_info_for_port = AsyncMock(  # type: ignore[method-assign]
        return_value={"device": {"TokenAuthSupport": "true"}}
    )

    with pytest.raises(AuthenticationError, match="replaced its stored token"):
        await adapter.connect()

    assert saved == []
    assert ReplacingRemote.instances[0].closed
