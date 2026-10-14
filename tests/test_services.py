"""Tests for Samsung Local's Home Assistant action interface."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import homeassistant
import pytest

if getattr(homeassistant, "__file__", None) is None:
    pytest.skip("Home Assistant test harness is not installed", allow_module_level=True)

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.samsung_local.const import (
    CONF_PROTOCOL,
    DOMAIN,
    PROTOCOL_TIZEN,
    SERVICE_LAUNCH_APP,
)
from custom_components.samsung_local.services import (
    async_register_services,
    async_unregister_services,
)

pytestmark = pytest.mark.homeassistant


async def test_launch_app_service_targets_loaded_tv(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    command = AsyncMock()
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PROTOCOL: PROTOCOL_TIZEN},
        state=ConfigEntryState.LOADED,
    )
    entry.runtime_data = SimpleNamespace(async_command=command)
    entry.add_to_hass(hass)
    async_register_services(hass)

    with patch(
        "custom_components.samsung_local.services.async_extract_config_entry_ids",
        AsyncMock(return_value={entry.entry_id}),
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_LAUNCH_APP,
            {
                "entity_id": "media_player.bedroom_tv",
                "app": "amazon prime",
                "turn_on": True,
            },
            blocking=True,
        )

    command.assert_awaited_once_with("launch_app", value="amazon prime", turn_on=True)
    async_unregister_services(hass)
    assert not hass.services.has_service(DOMAIN, SERVICE_LAUNCH_APP)


async def test_launch_app_service_rejects_non_samsung_target(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    async_register_services(hass)
    with (
        patch(
            "custom_components.samsung_local.services.async_extract_config_entry_ids",
            AsyncMock(return_value=set()),
        ),
        pytest.raises(ServiceValidationError),
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_LAUNCH_APP,
            {"entity_id": "media_player.other_tv", "app": "netflix"},
            blocking=True,
        )
