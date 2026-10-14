"""Home Assistant actions exposed by Samsung Local."""

from __future__ import annotations

import asyncio

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_extract_config_entry_ids

from .const import (
    ATTR_APP,
    ATTR_TURN_ON,
    CONF_PROTOCOL,
    DOMAIN,
    PROTOCOL_TIZEN,
    SERVICE_LAUNCH_APP,
)
from .exceptions import SamsungLocalError

LAUNCH_APP_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Required(ATTR_APP): vol.All(cv.string, vol.Length(min=1, max=128)),
        vol.Optional(ATTR_TURN_ON, default=True): cv.boolean,
    }
)


async def _async_launch_app(call: ServiceCall) -> None:
    """Resolve target config entries and use their shared adapter launcher."""
    target_entry_ids = await async_extract_config_entry_ids(call)
    entries = [
        entry
        for entry_id in target_entry_ids
        if (entry := call.hass.config_entries.async_get_entry(entry_id)) is not None
        and entry.domain == DOMAIN
        and entry.state is ConfigEntryState.LOADED
        and entry.data.get(CONF_PROTOCOL) == PROTOCOL_TIZEN
    ]
    if not entries:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_tv_target",
        )

    try:
        await asyncio.gather(
            *(
                entry.runtime_data.async_command(
                    "launch_app",
                    value=call.data[ATTR_APP],
                    turn_on=call.data[ATTR_TURN_ON],
                )
                for entry in entries
            )
        )
    except SamsungLocalError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="app_launch_failed",
            translation_placeholders={"error": str(err)},
        ) from err


@callback
def async_register_services(hass: HomeAssistant) -> None:
    """Register integration actions once while at least one entry is loaded."""
    if hass.services.has_service(DOMAIN, SERVICE_LAUNCH_APP):
        return
    hass.services.async_register(
        DOMAIN,
        SERVICE_LAUNCH_APP,
        _async_launch_app,
        schema=LAUNCH_APP_SCHEMA,
    )


@callback
def async_unregister_services(hass: HomeAssistant) -> None:
    """Remove actions after the final Samsung Local entry unloads."""
    if hass.services.has_service(DOMAIN, SERVICE_LAUNCH_APP):
        hass.services.async_remove(DOMAIN, SERVICE_LAUNCH_APP)
