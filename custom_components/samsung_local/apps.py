"""Per-TV application registry and safe alias resolution."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from .exceptions import InvalidCommandError

APP_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


class AppLaunchMethod(StrEnum):
    """Local launch mechanisms exposed by Tizen firmware."""

    AUTO = "auto"
    DEEP_LINK = "DEEP_LINK"
    NATIVE_LAUNCH = "NATIVE_LAUNCH"
    REST = "REST"


class AppSupportStatus(StrEnum):
    """How strongly an app is known for one TV."""

    KNOWN_CANDIDATE = "known_candidate"
    DISCOVERED = "discovered"
    MANUAL = "manual"
    VERIFIED = "verified"


class AppLaunchStatus(StrEnum):
    """Strongest confirmation available after a launch."""

    COMMAND_SENT = "command_sent"
    DEVICE_CONFIRMED = "device_confirmed"
    ACTIVE = "active"
    ACTIVATION_UNVERIFIABLE = "activation_unverifiable"
    FAILED = "failed"


@dataclass(slots=True)
class TvApplication:
    """One logical app with bounded, device-specific ID candidates."""

    key: str
    name: str
    app_ids: tuple[str, ...]
    aliases: tuple[str, ...] = ()
    method: AppLaunchMethod = AppLaunchMethod.AUTO
    status: AppSupportStatus = AppSupportStatus.KNOWN_CANDIDATE
    enabled: bool = True
    last_success: datetime | None = None


@dataclass(frozen=True, slots=True)
class AppLaunchResult:
    """Protocol result without claiming an unobservable active app."""

    key: str
    app_id: str
    method: AppLaunchMethod
    status: AppLaunchStatus
    command_sent: bool
    device_confirmed: bool
    active: bool | None


KNOWN_APPLICATIONS: tuple[TvApplication, ...] = (
    TvApplication(
        "netflix",
        "Netflix",
        ("3201907018807", "11101200001"),
        ("netflix",),
    ),
    TvApplication(
        "prime_video",
        "Prime Video",
        ("3201910019365", "3201512006785"),
        ("prime", "prime video", "amazon prime", "amazon prime video"),
    ),
    TvApplication("youtube", "YouTube", ("111299001912",), ("youtube", "you tube")),
    TvApplication(
        "disney_plus", "Disney+", ("3201901017640",), ("disney", "disney plus", "disney+")
    ),
    TvApplication("spotify", "Spotify", ("3201606009684",), ("spotify",)),
    TvApplication("plex", "Plex", ("3201512006963",), ("plex",)),
    TvApplication("apple_tv", "Apple TV", ("3201807016597",), ("apple tv", "appletv")),
)


def normalize_app_alias(value: str) -> str:
    """Normalize human speech without accepting arbitrary command syntax."""
    return "".join(character for character in value.casefold() if character.isalnum())


def normalize_app_key(value: str) -> str:
    """Create a stable registry key while preserving meaningful separators."""
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def _validate_app_id(value: str) -> str:
    value = value.strip()
    if not APP_ID_PATTERN.fullmatch(value):
        raise InvalidCommandError(
            "app IDs may contain only letters, digits, dot, dash and underscore"
        )
    return value


class TvAppRegistry:
    """Merge known candidates, explicit mappings and device discovery."""

    def __init__(self, configured: list[dict[str, Any]] | None = None) -> None:
        self._apps: dict[str, TvApplication] = {
            app.key: TvApplication(
                app.key, app.name, app.app_ids, app.aliases, app.method, app.status
            )
            for app in KNOWN_APPLICATIONS
        }
        self._discovered_ids: set[str] = set()
        self._manual_keys: set[str] = set()
        self._last_launch: AppLaunchResult | None = None
        for item in configured or []:
            self.add_configured(item)

    def add_configured(self, item: dict[str, Any]) -> None:
        """Add or replace one validated user mapping."""
        key = normalize_app_key(str(item.get("key", "")))
        name = str(item.get("name", "")).strip()
        raw_ids = item.get("app_ids", ())
        if not key or not name or not isinstance(raw_ids, (list, tuple)):
            raise InvalidCommandError("configured app requires key, name and app IDs")
        app_ids = tuple(dict.fromkeys(_validate_app_id(str(value)) for value in raw_ids))
        if not app_ids:
            raise InvalidCommandError("configured app requires at least one app ID")
        aliases = tuple(
            alias.strip()
            for alias in item.get("aliases", ())
            if isinstance(alias, str) and alias.strip()
        )
        if (previous := self._apps.get(key)) is not None:
            aliases = tuple(dict.fromkeys((*previous.aliases, *aliases)))
        candidate_aliases = {
            normalize_app_alias(key),
            normalize_app_alias(name),
            *(normalize_app_alias(alias) for alias in aliases),
        }
        for existing_key, existing in self._apps.items():
            if existing_key == key:
                continue
            existing_aliases = {
                normalize_app_alias(existing.key),
                normalize_app_alias(existing.name),
                *(normalize_app_alias(alias) for alias in existing.aliases),
            }
            if candidate_aliases & existing_aliases:
                raise InvalidCommandError("configured app alias is ambiguous for this TV")
        try:
            method = AppLaunchMethod(str(item.get("method", AppLaunchMethod.AUTO)))
        except ValueError as err:
            raise InvalidCommandError("configured app launch method is invalid") from err
        self._apps[key] = TvApplication(
            key=key,
            name=name,
            app_ids=app_ids,
            aliases=aliases,
            method=method,
            status=AppSupportStatus.MANUAL,
            enabled=bool(item.get("enabled", True)),
        )
        self._manual_keys.add(key)

    def add_discovered(self, name: str, app_id: str) -> None:
        """Record an app actually advertised by this TV."""
        app_id = _validate_app_id(app_id)
        normalized_name = normalize_app_alias(name)
        existing = self._find_by_alias(normalized_name)
        if existing is None:
            key = normalized_name or normalize_app_alias(app_id)
            existing = TvApplication(
                key=key,
                name=name.strip() or app_id,
                app_ids=(app_id,),
                aliases=(name,),
                status=AppSupportStatus.DISCOVERED,
            )
            self._apps[key] = existing
        elif app_id not in existing.app_ids:
            existing.app_ids = (app_id, *existing.app_ids)
        if existing.status is AppSupportStatus.KNOWN_CANDIDATE:
            existing.status = AppSupportStatus.DISCOVERED
        self._discovered_ids.add(app_id)

    def _find_by_alias(self, normalized: str) -> TvApplication | None:
        matches = [
            app
            for app in self._apps.values()
            if normalized
            in {
                normalize_app_alias(app.key),
                normalize_app_alias(app.name),
                *(normalize_app_alias(alias) for alias in app.aliases),
            }
        ]
        if len(matches) > 1:
            raise InvalidCommandError("app alias is ambiguous for this TV")
        return matches[0] if matches else None

    def resolve(self, value: str) -> TvApplication:
        """Resolve a name, alias or registered ID; never accept arbitrary payloads."""
        query = value.strip()
        if not query:
            raise InvalidCommandError("app name must not be empty")
        by_id = [app for app in self._apps.values() if query in app.app_ids and app.enabled]
        if len(by_id) == 1:
            return by_id[0]
        app = self._find_by_alias(normalize_app_alias(query))
        if app is None or not app.enabled:
            raise InvalidCommandError(f"unknown or disabled TV app {value!r}")
        return app

    def exposed_apps(self) -> tuple[TvApplication, ...]:
        """Expose only discovered, manual or previously verified apps as sources."""
        return tuple(
            sorted(
                (
                    app
                    for app in self._apps.values()
                    if app.enabled
                    and (
                        app.key in self._manual_keys
                        or bool(set(app.app_ids) & self._discovered_ids)
                        or app.status is AppSupportStatus.VERIFIED
                    )
                ),
                key=lambda app: app.name.casefold(),
            )
        )

    def all_apps(self) -> tuple[TvApplication, ...]:
        """Return known and configured records for explicit testing/selection."""
        return tuple(sorted(self._apps.values(), key=lambda app: app.name.casefold()))

    def record_launch(self, app: TvApplication, result: AppLaunchResult, when: datetime) -> None:
        self._last_launch = result
        if result.device_confirmed or result.active is True:
            app.last_success = when
        if result.status in {AppLaunchStatus.DEVICE_CONFIRMED, AppLaunchStatus.ACTIVE}:
            app.status = AppSupportStatus.VERIFIED

    @property
    def last_launch(self) -> AppLaunchResult | None:
        return self._last_launch

    def diagnostics(self) -> dict[str, Any]:
        """Return IDs only as counts; app IDs can still fingerprint firmware/region."""
        exposed = self.exposed_apps()
        return {
            "known_count": len(self._apps),
            "discovered_count": len(self._discovered_ids),
            "manual_count": len(self._manual_keys),
            "exposed_apps": [app.key for app in exposed],
            "support": {app.key: app.status.value for app in exposed},
            "last_success": {app.key: app.last_success for app in exposed},
            "last_launch": (
                {
                    "key": self._last_launch.key,
                    "method": self._last_launch.method.value,
                    "status": self._last_launch.status.value,
                    "command_sent": self._last_launch.command_sent,
                    "device_confirmed": self._last_launch.device_confirmed,
                    "active": self._last_launch.active,
                }
                if self._last_launch
                else None
            ),
        }
