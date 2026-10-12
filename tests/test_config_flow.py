"""Home Assistant config-flow tests (collected only with the HA harness)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import homeassistant
import pytest

if getattr(homeassistant, "__file__", None) is None:
    pytest.skip("Home Assistant test harness is not installed", allow_module_level=True)

from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.samsung_local.const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_POLL_INTERVAL,
    CONF_PORT,
    CONF_PROTOCOL,
    DOMAIN,
    PROTOCOL_TIZEN,
)
from custom_components.samsung_local.exceptions import AuthenticationError
from custom_components.samsung_local.models import (
    Capability,
    DeviceCategory,
    DeviceInfo,
    DiscoveryResult,
    EntityPlatform,
    Protocol,
)
from tests.simulated import SimulatedSamsungAdapter

pytestmark = pytest.mark.homeassistant


async def test_tv_config_flow_pairs_confirms_and_closes(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    discovered = DiscoveryResult(
        host="192.0.2.30",
        protocol=Protocol.TIZEN,
        port=8002,
        name="Samsung TV",
        category=DeviceCategory.TV,
    )
    info = DeviceInfo(
        "tv-stable-id",
        "Living room TV",
        DeviceCategory.TV,
        Protocol.TIZEN,
        model="GQ55Q60CAUXZG",
    )
    media_capability = Capability("media_player", EntityPlatform.MEDIA_PLAYER)
    runtime_adapter = SimulatedSamsungAdapter(info, [{"media_player": media_capability}])
    with (
        patch(
            "custom_components.samsung_local.config_flow.async_discover_host",
            AsyncMock(return_value=[discovered]),
        ),
        patch(
            "custom_components.samsung_local.config_flow.TizenTvAdapter.connect",
            AsyncMock(),
        ),
        patch(
            "custom_components.samsung_local.config_flow.TizenTvAdapter.disconnect",
            AsyncMock(),
        ) as disconnect,
        patch(
            "custom_components.samsung_local.config_flow.TizenTvAdapter.get_device_info",
            AsyncMock(return_value=info),
        ),
        patch(
            "custom_components.samsung_local.config_flow.TizenTvAdapter.get_capabilities",
            AsyncMock(return_value={"media_player": media_capability}),
        ),
        patch(
            "custom_components.samsung_local.build_adapter",
            return_value=runtime_adapter,
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={CONF_HOST: discovered.host, CONF_PROTOCOL: PROTOCOL_TIZEN},
        )
        assert result["type"] is data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "pair"

        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
        assert result["type"] is data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "confirm"
        assert result["description_placeholders"]["capabilities"] == "1"

        # Rendering the form repeatedly must not consume the count.
        result = await hass.config_entries.flow.async_configure(result["flow_id"], None)
        assert result["description_placeholders"]["capabilities"] == "1"
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})

    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Living room TV"
    assert result["data"][CONF_DEVICE_ID] == "tv-stable-id"
    disconnect.assert_awaited_once()
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(result["result"].entry_id)


async def test_options_flow_validates_polling_bounds(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TV",
        unique_id="tv-options",
        data={
            CONF_HOST: "192.0.2.31",
            CONF_PROTOCOL: PROTOCOL_TIZEN,
            CONF_PORT: 8002,
            CONF_DEVICE_ID: "tv-options",
            CONF_DEVICE_TYPE: "tv",
        },
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is data_entry_flow.FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_POLL_INTERVAL: 45,
            "enable_wol": False,
            "allow_writes_without_remote": False,
            "debug_diagnostics": False,
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_POLL_INTERVAL] == 45


@pytest.mark.parametrize(
    ("probe_result", "expected_error"),
    [([], "cannot_connect"), (ValueError("bad host"), "invalid_host")],
)
async def test_user_flow_reports_probe_errors(
    hass: HomeAssistant,
    enable_custom_integrations: None,
    probe_result: object,
    expected_error: str,
) -> None:
    probe = (
        AsyncMock(side_effect=probe_result)
        if isinstance(probe_result, Exception)
        else AsyncMock(return_value=probe_result)
    )
    with patch("custom_components.samsung_local.config_flow.async_discover_host", probe):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={CONF_HOST: "invalid/host", CONF_PROTOCOL: PROTOCOL_TIZEN},
        )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"]["base"] == expected_error


async def test_pairing_rejection_is_reported_and_session_is_closed(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    discovered = DiscoveryResult(
        host="192.0.2.60",
        protocol=Protocol.TIZEN,
        port=8002,
        name="Samsung TV",
        category=DeviceCategory.TV,
    )
    with patch(
        "custom_components.samsung_local.config_flow.async_discover_host",
        AsyncMock(return_value=[discovered]),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={CONF_HOST: discovered.host, CONF_PROTOCOL: PROTOCOL_TIZEN},
        )
    with (
        patch(
            "custom_components.samsung_local.config_flow.TizenTvAdapter.connect",
            AsyncMock(side_effect=AuthenticationError("denied")),
        ),
        patch(
            "custom_components.samsung_local.config_flow.TizenTvAdapter.disconnect",
            AsyncMock(),
        ) as disconnect,
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "pair"
    assert result["errors"]["base"] == "auth_rejected"
    disconnect.assert_awaited_once()


async def test_reconfigure_updates_only_a_verified_address(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TV",
        unique_id="tv-reconfigure",
        data={
            CONF_HOST: "192.0.2.70",
            CONF_PROTOCOL: PROTOCOL_TIZEN,
            CONF_PORT: 8002,
            CONF_DEVICE_ID: "tv-reconfigure",
            CONF_DEVICE_TYPE: "tv",
        },
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )
    assert result["step_id"] == "reconfigure"
    replacement = DiscoveryResult(
        host="192.0.2.71",
        protocol=Protocol.TIZEN,
        port=8001,
        name="TV",
        category=DeviceCategory.TV,
    )
    runtime_adapter = SimulatedSamsungAdapter(
        DeviceInfo("tv-reconfigure", "TV", DeviceCategory.TV, Protocol.SIMULATED),
        [{"media_player": Capability("media_player", EntityPlatform.MEDIA_PLAYER)}],
    )
    with (
        patch(
            "custom_components.samsung_local.config_flow.async_discover_host",
            AsyncMock(return_value=[replacement]),
        ),
        patch(
            "custom_components.samsung_local.build_adapter",
            return_value=runtime_adapter,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: replacement.host}
        )
        await hass.async_block_till_done()
    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert entry.data[CONF_HOST] == replacement.host
    assert entry.data[CONF_PORT] == 8001
    if entry.state is config_entries.ConfigEntryState.LOADED:
        assert await hass.config_entries.async_unload(entry.entry_id)
