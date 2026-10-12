"""UI-only setup, reconfigure, reauthentication and options flows."""

from __future__ import annotations

from typing import Any

try:
    import probatio as vol
except ImportError:  # Home Assistant before the probatio migration.
    import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
from homeassistant.helpers.service_info.ssdp import SsdpServiceInfo
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .adapters.legacy_appliance import LegacyApplianceAdapter
from .adapters.ocf_appliance import OcfApplianceAdapter
from .adapters.tizen_tv import TizenTvAdapter
from .authentication.manager import AuthenticationManager, OcfCredentialKind
from .const import (
    AUTH_CERTIFICATE,
    AUTH_PSK,
    CONF_ALLOW_WRITES_WITHOUT_REMOTE,
    CONF_AUTH_TYPE,
    CONF_CERTIFICATE,
    CONF_DEBUG_DIAGNOSTICS,
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_ENABLE_WOL,
    CONF_FIRMWARE,
    CONF_MAC,
    CONF_MODEL,
    CONF_POLL_INTERVAL,
    CONF_PORT,
    CONF_PRIVATE_KEY,
    CONF_PROTOCOL,
    CONF_PSK_IDENTITY,
    CONF_PSK_KEY,
    CONF_TOKEN,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    MAX_POLL_INTERVAL,
    MIN_POLL_INTERVAL,
    PROTOCOL_LEGACY,
    PROTOCOL_OCF,
    PROTOCOL_TIZEN,
)
from .discovery import async_discover_host, host_from_discovery_url
from .exceptions import AuthenticationError, CannotConnectError
from .models import DiscoveryResult, Protocol

PROTOCOL_AUTO = "auto"
AUTH_AUTO_ONLINE = "auto_online"
AUTH_MANUAL_IDENTITY = "manual_identity"

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PROTOCOL, default=PROTOCOL_AUTO): vol.In(
            [PROTOCOL_AUTO, PROTOCOL_TIZEN, PROTOCOL_OCF, PROTOCOL_LEGACY]
        ),
    }
)

OCF_AUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_AUTH_TYPE, default=AUTH_AUTO_ONLINE): vol.In(
            [AUTH_AUTO_ONLINE, AUTH_MANUAL_IDENTITY, AUTH_CERTIFICATE, AUTH_PSK]
        ),
        vol.Optional("public_identity"): str,
        vol.Optional(CONF_CERTIFICATE): str,
        vol.Optional(CONF_PRIVATE_KEY): str,
        vol.Optional(CONF_PSK_IDENTITY): str,
        vol.Optional(CONF_PSK_KEY): str,
    }
)

LEGACY_AUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TOKEN): str,
        vol.Required(CONF_CERTIFICATE): str,
        vol.Required(CONF_PRIVATE_KEY): str,
    }
)


class SamsungLocalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure Samsung Local from the Home Assistant UI."""

    VERSION = 1

    def __init__(self) -> None:
        self._host = ""
        self._discovery: DiscoveryResult | None = None
        self._pending: dict[str, Any] | None = None
        self._title = "Samsung Local"
        self._reauth_entry: config_entries.ConfigEntry | None = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SamsungLocalOptionsFlow:
        return SamsungLocalOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._host = user_input[CONF_HOST].strip()
            protocol_value = user_input[CONF_PROTOCOL]
            preferred = None if protocol_value == PROTOCOL_AUTO else Protocol(protocol_value)
            try:
                results = await async_discover_host(
                    async_get_clientsession(self.hass), self._host, preferred_protocol=preferred
                )
            except ValueError:
                errors["base"] = "invalid_host"
            else:
                if not results:
                    errors["base"] = "cannot_connect"
                else:
                    self._discovery = results[0]
                    return await self._async_route_authentication()
        return self.async_show_form(step_id="user", data_schema=USER_SCHEMA, errors=errors)

    async def _async_route_authentication(self) -> ConfigFlowResult:
        assert self._discovery is not None
        if self._discovery.protocol is Protocol.TIZEN:
            return await self.async_step_pair()
        if self._discovery.protocol is Protocol.OCF:
            return await self.async_step_ocf_auth()
        return await self.async_step_legacy_auth()

    async def async_step_pair(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Pair immediately; the TV displays its own consent prompt."""
        assert self._discovery is not None
        errors: dict[str, str] = {}
        if user_input is not None:
            adapter = TizenTvAdapter(
                self._host,
                async_get_clientsession(self.hass),
                port=self._discovery.port,
                token=(self._reauth_entry.data.get(CONF_TOKEN) if self._reauth_entry else None),
            )
            try:
                await adapter.connect()
                info = await adapter.get_device_info()
                capabilities = await adapter.get_capabilities()
            except AuthenticationError:
                errors["base"] = "auth_rejected"
            except CannotConnectError:
                errors["base"] = "cannot_connect"
            else:
                self._pending = {
                    CONF_HOST: self._host,
                    CONF_PROTOCOL: PROTOCOL_TIZEN,
                    CONF_PORT: adapter.port,
                    CONF_TOKEN: adapter.token,
                    CONF_DEVICE_ID: info.device_id,
                    CONF_DEVICE_TYPE: info.category.value,
                    CONF_MODEL: info.model,
                    CONF_FIRMWARE: info.firmware,
                    CONF_MAC: info.mac_address,
                    "capability_count": len(capabilities),
                }
                self._title = info.name
                return await self.async_step_confirm()
            finally:
                await adapter.disconnect()
        return self.async_show_form(
            step_id="pair",
            data_schema=vol.Schema({}),
            errors=errors,
            description_placeholders={"host": self._host},
        )

    async def async_step_ocf_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        assert self._discovery is not None
        errors: dict[str, str] = {}
        if user_input is not None:
            manager = AuthenticationManager()
            mode = user_input[CONF_AUTH_TYPE]
            adapter: OcfApplianceAdapter | None = None
            try:
                if mode in {AUTH_AUTO_ONLINE, AUTH_MANUAL_IDENTITY}:
                    public_identity = (
                        user_input.get("public_identity") if mode == AUTH_MANUAL_IDENTITY else None
                    )
                    credentials = await manager.async_generate_ocf_credentials(public_identity)
                elif mode == AUTH_CERTIFICATE:
                    credentials = await manager.async_import_certificate(
                        user_input.get(CONF_CERTIFICATE, ""),
                        user_input.get(CONF_PRIVATE_KEY, ""),
                    )
                else:
                    credentials = await manager.async_import_psk(
                        user_input.get(CONF_PSK_IDENTITY, ""),
                        user_input.get(CONF_PSK_KEY, ""),
                    )
                adapter = OcfApplianceAdapter(self._host, self._discovery.port, credentials)
                await adapter.connect()
                info = await adapter.get_device_info()
                capabilities = await adapter.get_capabilities()
            except ValueError:
                errors["base"] = "invalid_auth"
            except AuthenticationError:
                errors["base"] = "auth_rejected"
            except CannotConnectError:
                errors["base"] = "cannot_connect"
            except (OSError, RuntimeError):
                errors["base"] = "public_identity_unavailable"
            else:
                self._pending = {
                    CONF_HOST: self._host,
                    CONF_PROTOCOL: PROTOCOL_OCF,
                    CONF_PORT: self._discovery.port,
                    CONF_AUTH_TYPE: credentials.kind.value,
                    CONF_DEVICE_ID: info.device_id,
                    CONF_DEVICE_TYPE: info.category.value,
                    CONF_MODEL: info.model,
                    CONF_FIRMWARE: info.firmware,
                    "capability_count": len(capabilities),
                }
                if credentials.kind is OcfCredentialKind.CERTIFICATE:
                    self._pending[CONF_CERTIFICATE] = credentials.certificate_pem
                    self._pending[CONF_PRIVATE_KEY] = credentials.private_key_pem
                else:
                    self._pending[CONF_PSK_IDENTITY] = credentials.psk_identity
                    self._pending[CONF_PSK_KEY] = credentials.psk_key
                self._title = info.name
                return await self.async_step_confirm()
            finally:
                if adapter is not None:
                    await adapter.disconnect()
        return self.async_show_form(
            step_id="ocf_auth",
            data_schema=OCF_AUTH_SCHEMA,
            errors=errors,
            description_placeholders={"host": self._host},
        )

    async def async_step_legacy_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        assert self._discovery is not None
        errors: dict[str, str] = {}
        if user_input is not None:
            manager = AuthenticationManager()
            adapter: LegacyApplianceAdapter | None = None
            try:
                credentials = await manager.async_import_certificate(
                    user_input[CONF_CERTIFICATE], user_input[CONF_PRIVATE_KEY]
                )
                adapter = LegacyApplianceAdapter(
                    self._host,
                    user_input[CONF_TOKEN],
                    credentials.certificate_pem or "",
                    credentials.private_key_pem or "",
                    self._discovery.port,
                )
                await adapter.connect()
                info = await adapter.get_device_info()
                capabilities = await adapter.get_capabilities()
            except ValueError:
                errors["base"] = "invalid_auth"
            except AuthenticationError:
                errors["base"] = "auth_rejected"
            except CannotConnectError:
                errors["base"] = "legacy_not_supported"
            else:
                self._pending = {
                    CONF_HOST: self._host,
                    CONF_PROTOCOL: PROTOCOL_LEGACY,
                    CONF_PORT: self._discovery.port,
                    CONF_AUTH_TYPE: AUTH_CERTIFICATE,
                    CONF_TOKEN: user_input[CONF_TOKEN],
                    CONF_CERTIFICATE: credentials.certificate_pem,
                    CONF_PRIVATE_KEY: credentials.private_key_pem,
                    CONF_DEVICE_ID: info.device_id,
                    CONF_DEVICE_TYPE: info.category.value,
                    CONF_MODEL: info.model,
                    "capability_count": len(capabilities),
                }
                self._title = info.name
                return await self.async_step_confirm()
            finally:
                if adapter is not None:
                    await adapter.disconnect()
        return self.async_show_form(
            step_id="legacy_auth",
            data_schema=LEGACY_AUTH_SCHEMA,
            errors=errors,
            description_placeholders={"host": self._host},
        )

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        assert self._pending is not None
        if user_input is None:
            return self.async_show_form(
                step_id="confirm",
                data_schema=vol.Schema({}),
                description_placeholders={
                    "name": self._title,
                    "model": str(self._pending.get(CONF_MODEL) or "unknown"),
                    "protocol": self._pending[CONF_PROTOCOL],
                    "capabilities": str(self._pending.get("capability_count", 0)),
                },
            )
        self._pending.pop("capability_count", None)
        unique_id = str(self._pending[CONF_DEVICE_ID])
        await self.async_set_unique_id(unique_id)
        if self._reauth_entry is not None:
            return self.async_update_reload_and_abort(
                self._reauth_entry,
                data_updates=self._pending,
                reason="reauth_successful",
            )
        self._abort_if_unique_id_configured(updates={CONF_HOST: self._host})
        return self.async_create_entry(title=self._title, data=self._pending)

    async def async_step_dhcp(self, discovery_info: DhcpServiceInfo) -> ConfigFlowResult:
        self._host = discovery_info.ip
        for entry in self._async_current_entries():
            if entry.data.get(CONF_MAC) == discovery_info.macaddress:
                self.hass.config_entries.async_update_entry(
                    entry, data={**entry.data, CONF_HOST: self._host}
                )
                return self.async_abort(reason="already_configured")
        return await self.async_step_discovery_confirm()

    async def async_step_ssdp(self, discovery_info: SsdpServiceInfo) -> ConfigFlowResult:
        location = discovery_info.ssdp_location
        host = host_from_discovery_url(location) if location else None
        if not host:
            return self.async_abort(reason="invalid_host")
        self._host = host
        return await self.async_step_discovery_confirm()

    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo) -> ConfigFlowResult:
        self._host = discovery_info.host
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is None:
            self.context["title_placeholders"] = {"name": self._host}
            return self.async_show_form(
                step_id="discovery_confirm",
                data_schema=vol.Schema({}),
                description_placeholders={"host": self._host},
            )
        results = await async_discover_host(async_get_clientsession(self.hass), self._host)
        if not results:
            return self.async_abort(reason="cannot_connect")
        self._discovery = results[0]
        return await self._async_route_authentication()

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        if user_input is None:
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=vol.Schema(
                    {vol.Required(CONF_HOST, default=entry.data[CONF_HOST]): str}
                ),
            )
        self._host = user_input[CONF_HOST].strip()
        results = await async_discover_host(
            async_get_clientsession(self.hass),
            self._host,
            preferred_protocol=Protocol(entry.data[CONF_PROTOCOL]),
        )
        if not results:
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=vol.Schema({vol.Required(CONF_HOST, default=self._host): str}),
                errors={"base": "cannot_connect"},
            )
        return self.async_update_reload_and_abort(
            entry,
            data_updates={CONF_HOST: self._host, CONF_PORT: results[0].port},
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        self._reauth_entry = self._get_reauth_entry()
        self._host = self._reauth_entry.data[CONF_HOST]
        self._discovery = DiscoveryResult(
            host=self._host,
            protocol=Protocol(self._reauth_entry.data[CONF_PROTOCOL]),
            port=self._reauth_entry.data[CONF_PORT],
            name=self._reauth_entry.title,
        )
        return await self._async_route_authentication()


class SamsungLocalOptionsFlow(config_entries.OptionsFlow):
    """Per-device reliability and explicit safety options."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_POLL_INTERVAL,
                        default=options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
                    ): vol.All(vol.Coerce(int), vol.Range(MIN_POLL_INTERVAL, MAX_POLL_INTERVAL)),
                    vol.Required(
                        CONF_ENABLE_WOL,
                        default=options.get(CONF_ENABLE_WOL, False),
                    ): bool,
                    vol.Required(
                        CONF_ALLOW_WRITES_WITHOUT_REMOTE,
                        default=options.get(CONF_ALLOW_WRITES_WITHOUT_REMOTE, False),
                    ): bool,
                    vol.Required(
                        CONF_DEBUG_DIAGNOSTICS,
                        default=options.get(CONF_DEBUG_DIAGNOSTICS, False),
                    ): bool,
                }
            ),
        )
