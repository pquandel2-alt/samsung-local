"""Construct adapters from validated config entries."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .adapters.base import SamsungDeviceAdapter
from .adapters.legacy_appliance import LegacyApplianceAdapter
from .adapters.ocf_appliance import OcfApplianceAdapter
from .adapters.tizen_tv import TizenTvAdapter
from .authentication.manager import OcfCredentialKind, OcfCredentials
from .const import (
    AUTH_CERTIFICATE,
    CONF_ALLOW_WRITES_WITHOUT_REMOTE,
    CONF_AUTH_TYPE,
    CONF_CERTIFICATE,
    CONF_DEVICE_ID,
    CONF_ENABLE_WOL,
    CONF_FIRMWARE,
    CONF_MAC,
    CONF_MODEL,
    CONF_PORT,
    CONF_POWER_ON_TIMEOUT,
    CONF_PRIVATE_KEY,
    CONF_PROTOCOL,
    CONF_PSK_IDENTITY,
    CONF_PSK_KEY,
    CONF_TOKEN,
    CONF_TV_APPS,
    CONF_WOL_BROADCAST,
    CONF_WOL_PORT,
    CONF_WOL_RETRIES,
    DEFAULT_POWER_ON_TIMEOUT,
    DEFAULT_WOL_BROADCAST,
    DEFAULT_WOL_PORT,
    DEFAULT_WOL_RETRIES,
    PROTOCOL_LEGACY,
    PROTOCOL_OCF,
    PROTOCOL_TIZEN,
)


def _combined(entry: ConfigEntry) -> dict[str, Any]:
    return {**entry.data, **entry.options}


def build_adapter(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> SamsungDeviceAdapter:
    """Build but do not connect the selected protocol adapter."""
    data = _combined(entry)
    host = data["host"]
    protocol = data[CONF_PROTOCOL]
    if protocol == PROTOCOL_TIZEN:

        @callback
        def save_token(token: str) -> None:
            if token == entry.data.get(CONF_TOKEN):
                return
            hass.config_entries.async_update_entry(entry, data={**entry.data, CONF_TOKEN: token})

        return TizenTvAdapter(
            host,
            async_get_clientsession(hass),
            port=data.get(CONF_PORT),
            token=data.get(CONF_TOKEN),
            mac_address=data.get(CONF_MAC),
            enable_wol=data.get(CONF_ENABLE_WOL, False),
            wol_broadcast=data.get(CONF_WOL_BROADCAST, DEFAULT_WOL_BROADCAST),
            wol_port=data.get(CONF_WOL_PORT, DEFAULT_WOL_PORT),
            power_on_timeout=data.get(CONF_POWER_ON_TIMEOUT, DEFAULT_POWER_ON_TIMEOUT),
            wol_retries=data.get(CONF_WOL_RETRIES, DEFAULT_WOL_RETRIES),
            configured_apps=data.get(CONF_TV_APPS, []),
            configured_device_id=data.get(CONF_DEVICE_ID),
            configured_name=entry.title,
            configured_model=data.get(CONF_MODEL),
            configured_firmware=data.get(CONF_FIRMWARE),
            token_callback=save_token,
        )
    if protocol == PROTOCOL_OCF:
        if data.get(CONF_AUTH_TYPE) == AUTH_CERTIFICATE:
            credentials = OcfCredentials(
                OcfCredentialKind.CERTIFICATE,
                certificate_pem=data.get(CONF_CERTIFICATE),
                private_key_pem=data.get(CONF_PRIVATE_KEY),
            )
        else:
            credentials = OcfCredentials(
                OcfCredentialKind.PSK,
                psk_identity=data.get(CONF_PSK_IDENTITY),
                psk_key=data.get(CONF_PSK_KEY),
            )
        return OcfApplianceAdapter(
            host,
            data[CONF_PORT],
            credentials,
            allow_writes_without_remote=data.get(CONF_ALLOW_WRITES_WITHOUT_REMOTE, False),
        )
    if protocol == PROTOCOL_LEGACY:
        return LegacyApplianceAdapter(
            host,
            data[CONF_TOKEN],
            data[CONF_CERTIFICATE],
            data[CONF_PRIVATE_KEY],
            data.get(CONF_PORT, 8888),
        )
    raise ValueError(f"unsupported protocol {protocol!r}")
