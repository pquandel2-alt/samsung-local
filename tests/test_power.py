"""Tests for bounded and confirmed TV Wake-on-LAN."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.samsung_local.exceptions import CannotConnectError, InvalidCommandError
from custom_components.samsung_local.power import (
    SamsungTvPowerManager,
    WakeOnLanConfig,
    _send_magic_packet,
)


def test_sender_supports_wakeonlan_3_api(monkeypatch) -> None:
    sender = Mock()
    monkeypatch.setattr("custom_components.samsung_local.power.wakeonlan.send_magic_packet", sender)

    _send_magic_packet("02:00:00:00:00:01", "192.0.2.255", 9)

    sender.assert_called_once_with("02:00:00:00:00:01", ip_address="192.0.2.255", port=9)


def test_sender_supports_wakeonlan_4_api(monkeypatch) -> None:
    sender = Mock()
    monkeypatch.delattr("custom_components.samsung_local.power.wakeonlan.send_magic_packet")
    monkeypatch.setattr(
        "custom_components.samsung_local.power.wakeonlan.wake", sender, raising=False
    )

    _send_magic_packet("02:00:00:00:00:01", "192.0.2.255", 9)

    sender.assert_called_once_with("02:00:00:00:00:01", host="192.0.2.255", port=9)


@pytest.mark.parametrize(
    "config",
    [
        WakeOnLanConfig(True, None),
        WakeOnLanConfig(True, "02:00:00:00:00:01", "not-an-ip"),
        WakeOnLanConfig(True, "02:00:00:00:00:01", port=0),
        WakeOnLanConfig(True, "02:00:00:00:00:01", timeout=9),
        WakeOnLanConfig(True, "02:00:00:00:00:01", retries=6),
    ],
)
def test_invalid_wol_configuration_is_rejected(config: WakeOnLanConfig) -> None:
    with pytest.raises(InvalidCommandError):
        config.validate()


async def test_power_on_sends_packet_and_waits_for_endpoint(monkeypatch) -> None:
    sender = Mock()
    monkeypatch.setattr("custom_components.samsung_local.power._send_magic_packet", sender)
    monkeypatch.setattr("custom_components.samsung_local.power.asyncio.sleep", AsyncMock())
    manager = SamsungTvPowerManager(
        WakeOnLanConfig(
            True,
            "02:00:00:00:00:01",
            broadcast_address="192.0.2.255",
            timeout=10,
            retries=1,
        )
    )
    probe = AsyncMock(side_effect=[False, True])
    connect = AsyncMock()

    await manager.async_power_on(probe, connect)

    sender.assert_called_once_with("02:00:00:00:00:01", "192.0.2.255", 9)
    connect.assert_awaited_once()
    assert manager.last_success is not None


async def test_power_on_reports_packet_send_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        "custom_components.samsung_local.power._send_magic_packet",
        Mock(side_effect=OSError("network down")),
    )
    manager = SamsungTvPowerManager(
        WakeOnLanConfig(True, "02:00:00:00:00:01", timeout=10, retries=1)
    )

    with pytest.raises(CannotConnectError, match="could not be sent"):
        await manager.async_power_on(AsyncMock(return_value=False), AsyncMock())
    assert manager.last_error == "OSError"


async def test_power_on_times_out_when_tv_never_answers(monkeypatch) -> None:
    monkeypatch.setattr("custom_components.samsung_local.power._send_magic_packet", Mock())
    monkeypatch.setattr(WakeOnLanConfig, "validate", lambda self: None)
    manager = SamsungTvPowerManager(
        WakeOnLanConfig(True, "02:00:00:00:00:01", timeout=0.01, retries=1)
    )

    with pytest.raises(CannotConnectError, match="did not become ready"):
        await manager.async_power_on(AsyncMock(return_value=False), AsyncMock())
    assert manager.last_error == "power_on_timeout"


async def test_power_on_fails_when_websocket_never_reconnects(monkeypatch) -> None:
    monkeypatch.setattr("custom_components.samsung_local.power._send_magic_packet", Mock())
    monkeypatch.setattr(WakeOnLanConfig, "validate", lambda self: None)
    manager = SamsungTvPowerManager(
        WakeOnLanConfig(True, "02:00:00:00:00:01", timeout=0.01, retries=1)
    )

    with pytest.raises(CannotConnectError, match="did not become ready"):
        await manager.async_power_on(
            AsyncMock(side_effect=[False, True]),
            AsyncMock(side_effect=CannotConnectError("websocket unavailable")),
        )
    assert manager.last_success is None


async def test_power_on_does_not_send_when_tv_is_already_ready(monkeypatch) -> None:
    sender = Mock()
    monkeypatch.setattr("custom_components.samsung_local.power._send_magic_packet", sender)
    manager = SamsungTvPowerManager(
        WakeOnLanConfig(True, "02:00:00:00:00:01", timeout=10, retries=1)
    )
    connect = AsyncMock()

    await manager.async_power_on(AsyncMock(return_value=True), connect)

    sender.assert_not_called()
    connect.assert_awaited_once()
