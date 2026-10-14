"""Constants for Samsung Local."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "samsung_local"
LOGGER = logging.getLogger(__package__)

CONF_PROTOCOL = "protocol"
CONF_DEVICE_ID = "device_id"
CONF_DEVICE_TYPE = "device_type"
CONF_MODEL = "model"
CONF_FIRMWARE = "firmware"
CONF_MAC = "mac"
CONF_TOKEN = "token"
CONF_AUTH_TYPE = "auth_type"
CONF_CERTIFICATE = "certificate"
CONF_PRIVATE_KEY = "private_key"
CONF_PSK_IDENTITY = "psk_identity"
CONF_PSK_KEY = "psk_key"
CONF_PORT = "port"
CONF_ENABLE_WOL = "enable_wol"
CONF_WOL_BROADCAST = "wol_broadcast"
CONF_WOL_PORT = "wol_port"
CONF_POWER_ON_TIMEOUT = "power_on_timeout"
CONF_WOL_RETRIES = "wol_retries"
CONF_AUTO_RECONNECT = "auto_reconnect"
CONF_TV_APPS = "tv_apps"
CONF_POLL_INTERVAL = "poll_interval"
CONF_DEBUG_DIAGNOSTICS = "debug_diagnostics"
CONF_ALLOW_WRITES_WITHOUT_REMOTE = "allow_writes_without_remote"

PROTOCOL_TIZEN = "tizen"
PROTOCOL_OCF = "ocf"
PROTOCOL_LEGACY = "legacy"

AUTH_TOKEN = "token"
AUTH_CERTIFICATE = "certificate"
AUTH_PSK = "psk"
AUTH_NONE = "none"

DEFAULT_POLL_INTERVAL = 30
MIN_POLL_INTERVAL = 10
MAX_POLL_INTERVAL = 300
DEFAULT_UPDATE_INTERVAL = timedelta(seconds=DEFAULT_POLL_INTERVAL)
DEFAULT_WOL_BROADCAST = "255.255.255.255"
DEFAULT_WOL_PORT = 9
DEFAULT_POWER_ON_TIMEOUT = 45
DEFAULT_WOL_RETRIES = 3
DEFAULT_AUTO_RECONNECT = True
MIN_POWER_ON_TIMEOUT = 10
MAX_POWER_ON_TIMEOUT = 180
MIN_WOL_RETRIES = 1
MAX_WOL_RETRIES = 5

SERVICE_LAUNCH_APP = "launch_app"
ATTR_APP = "app"
ATTR_TURN_ON = "turn_on"

TIZEN_PORTS = (8002, 8001)
OCF_PORTS = tuple(range(49152, 49161))
OCF_FALLBACK_PORT = 5684
LEGACY_PORT = 8888
PAIRING_TIMEOUT = 35.0
REQUEST_TIMEOUT = 8.0

EVENT_PROGRAM_FINISHED = f"{DOMAIN}_program_finished"
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.completion"

PLATFORMS: tuple[Platform, ...] = (
    Platform.MEDIA_PLAYER,
    Platform.REMOTE,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.BUTTON,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.CLIMATE,
    Platform.FAN,
)

SENSITIVE_KEYS = {
    CONF_TOKEN,
    CONF_CERTIFICATE,
    CONF_PRIVATE_KEY,
    CONF_PSK_IDENTITY,
    CONF_PSK_KEY,
    CONF_WOL_BROADCAST,
    "serial",
    "serialNumber",
    "device_id",
    "di",
    "pi",
    "mac",
    "wifiMac",
    "host",
    "ip_address",
    "ssid",
    "email",
}
