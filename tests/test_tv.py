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
from custom_components.samsung_local.exceptions import (
    CommandNotSupportedError,
    InvalidCommandError,
)
from custom_components.samsung_local.models import ConnectionStatus


def test_tv_profiles_do_not_infer_model_from_firmware() -> None:
    fixture = json.loads((Path(__file__).parent / "fixtures" / "tv_8_series_43.json").read_text())
    assert fixture["device"]["modelName"] != fixture["device"]["firmwareVersion"]


def test_mac_normalization_rejects_placeholder() -> None:
    assert _normalize_mac("02-00-00-00-00-01") == "02:00:00:00:00:01"
    assert _normalize_mac("00:00:00:00:00:00") is None


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
        "custom_components.samsung_local.adapters.tizen_tv.SamsungTVWSAsyncRemote",
        FakeRemote,
    )
    tokens: list[str] = []
    adapter = TizenTvAdapter(
        "192.0.2.80",
        object(),  # type: ignore[arg-type]
        port=8002,
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
