"""End-to-end Home Assistant entity lifecycle with a deterministic adapter."""

from __future__ import annotations

from unittest.mock import patch

import homeassistant
import pytest

if getattr(homeassistant, "__file__", None) is None:
    pytest.skip("Home Assistant test harness is not installed", allow_module_level=True)

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.samsung_local.const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_PORT,
    CONF_PROTOCOL,
    DOMAIN,
    PROTOCOL_TIZEN,
)
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
