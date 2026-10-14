"""End-to-end Home Assistant entity lifecycle with a deterministic adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import homeassistant
import pytest

if getattr(homeassistant, "__file__", None) is None:
    pytest.skip("Home Assistant test harness is not installed", allow_module_level=True)

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.samsung_local.adapters.tizen_tv import TizenTvAdapter
from custom_components.samsung_local.const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_ENABLE_WOL,
    CONF_MAC,
    CONF_MODEL,
    CONF_PORT,
    CONF_PROTOCOL,
    CONF_TOKEN,
    DOMAIN,
    PROTOCOL_TIZEN,
    SERVICE_LAUNCH_APP,
)
from custom_components.samsung_local.exceptions import CannotConnectError
from custom_components.samsung_local.models import (
    Capability,
    DeviceCategory,
    DeviceInfo,
    EntityPlatform,
    Protocol,
)
from tests.simulated import SimulatedSamsungAdapter

pytestmark = pytest.mark.homeassistant


async def test_setup_creates_only_discovered_entities_and_unloads(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    info = DeviceInfo(
        "simulated-tv-id",
        "Virtual Q60C",
        DeviceCategory.TV,
        Protocol.SIMULATED,
        model="GQ55Q60CAUXZG",
    )
    adapter = SimulatedSamsungAdapter(
        info,
        [
            {
                "media_player": Capability("media_player", EntityPlatform.MEDIA_PLAYER, value="on"),
                "connection_status": Capability(
                    "connection_status", EntityPlatform.SENSOR, value="connected"
                ),
            }
        ],
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Virtual Q60C",
        unique_id=info.device_id,
        data={
            CONF_HOST: "192.0.2.50",
            CONF_PROTOCOL: PROTOCOL_TIZEN,
            CONF_PORT: 8002,
            CONF_DEVICE_ID: info.device_id,
            CONF_DEVICE_TYPE: "tv",
        },
    )
    entry.add_to_hass(hass)
    with patch("custom_components.samsung_local.build_adapter", return_value=adapter):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert hass.services.has_service(DOMAIN, SERVICE_LAUNCH_APP)
    entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    assert {entity.unique_id for entity in entities} == {
        "simulated-tv-id_media_player",
        "simulated-tv-id_connection_status",
    }
    assert {entity.domain for entity in entities} == {"media_player", "sensor"}
    assert all(hass.states.get(entity.entity_id) is not None for entity in entities)

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert adapter.connected is False
    assert not hass.services.has_service(DOMAIN, SERVICE_LAUNCH_APP)


async def test_configured_wol_tv_loads_while_deep_standby_is_unreachable(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """A HA restart in deep standby must still leave a callable WOL entity."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Bedroom TV",
        unique_id="bedroom-tv",
        data={
            CONF_HOST: "192.0.2.88",
            CONF_PROTOCOL: PROTOCOL_TIZEN,
            CONF_PORT: 8002,
            CONF_TOKEN: "stored-token",
            CONF_DEVICE_ID: "bedroom-tv",
            CONF_DEVICE_TYPE: "tv",
            CONF_MODEL: "GU43TU8079UXZG",
        },
        options={
            CONF_ENABLE_WOL: True,
            CONF_MAC: "02:00:00:00:00:88",
        },
    )
    entry.add_to_hass(hass)
    adapter = TizenTvAdapter(
        "192.0.2.88",
        object(),  # type: ignore[arg-type]
        port=8002,
        token="stored-token",
        mac_address="02:00:00:00:00:88",
        enable_wol=True,
        configured_device_id="bedroom-tv",
        configured_name="Bedroom TV",
        configured_model="GU43TU8079UXZG",
    )
    adapter.connect = AsyncMock(side_effect=CannotConnectError("deep standby"))  # type: ignore[method-assign]

    with patch("custom_components.samsung_local.build_adapter", return_value=adapter):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    media_entry = next(item for item in entities if item.domain == "media_player")
    state = hass.states.get(media_entry.entity_id)
    assert state is not None
    assert state.state == "unknown"
    assert state.attributes["supported_features"] > 0

    assert await hass.config_entries.async_unload(entry.entry_id)
