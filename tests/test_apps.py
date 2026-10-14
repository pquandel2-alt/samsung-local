"""Tests for device-specific Tizen app resolution."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from custom_components.samsung_local.apps import (
    AppLaunchMethod,
    AppLaunchResult,
    AppLaunchStatus,
    AppSupportStatus,
    TvAppRegistry,
    normalize_app_alias,
    normalize_app_key,
)
from custom_components.samsung_local.exceptions import InvalidCommandError


def test_known_aliases_are_normalized_without_exposing_candidates() -> None:
    registry = TvAppRegistry()

    assert normalize_app_alias(" Disney+ ") == "disney"
    assert normalize_app_key("My Stream") == "my_stream"
    assert registry.resolve("Amazon Prime Video").key == "prime_video"
    assert registry.resolve("3201907018807").key == "netflix"
    assert registry.exposed_apps() == ()


def test_manual_apps_are_per_device_and_validate_ids() -> None:
    bedroom = TvAppRegistry(
        [
            {
                "key": "my_stream",
                "name": "My Stream",
                "app_ids": ["org.example.stream"],
                "aliases": ["stream bitte"],
                "method": "NATIVE_LAUNCH",
            }
        ]
    )
    living_room = TvAppRegistry()

    app = bedroom.resolve("Stream bitte")
    assert app.app_ids == ("org.example.stream",)
    assert app.method is AppLaunchMethod.NATIVE_LAUNCH
    assert [item.key for item in bedroom.exposed_apps()] == ["my_stream"]
    with pytest.raises(InvalidCommandError, match="unknown"):
        living_room.resolve("stream bitte")
    with pytest.raises(InvalidCommandError, match="app IDs"):
        TvAppRegistry([{"key": "bad", "name": "Bad", "app_ids": ["bad payload/with slash"]}])


def test_manual_mapping_can_override_a_known_candidate_for_one_tv() -> None:
    registry = TvAppRegistry(
        [
            {
                "key": "prime_video",
                "name": "Prime Video",
                "app_ids": ["regional.prime.id"],
                "aliases": ["amazon prime"],
                "method": "REST",
            }
        ]
    )

    app = registry.resolve("prime")
    assert app.app_ids == ("regional.prime.id",)
    assert app.method is AppLaunchMethod.REST


def test_discovery_and_success_change_support_without_leaking_ids() -> None:
    registry = TvAppRegistry()
    registry.add_discovered("Netflix", "11101200001")
    app = registry.resolve("netflix")
    assert app.status is AppSupportStatus.DISCOVERED

    result = AppLaunchResult(
        key=app.key,
        app_id=app.app_ids[0],
        method=AppLaunchMethod.DEEP_LINK,
        status=AppLaunchStatus.ACTIVE,
        command_sent=True,
        device_confirmed=True,
        active=True,
    )
    registry.record_launch(app, result, datetime.now(UTC))

    diagnostics = registry.diagnostics()
    assert diagnostics["support"]["netflix"] == "verified"
    assert "11101200001" not in str(diagnostics)


def test_ambiguous_alias_is_rejected() -> None:
    with pytest.raises(InvalidCommandError, match="ambiguous"):
        TvAppRegistry(
            [
                {
                    "key": "one",
                    "name": "One",
                    "app_ids": ["one.id"],
                    "aliases": ["video"],
                },
                {
                    "key": "two",
                    "name": "Two",
                    "app_ids": ["two.id"],
                    "aliases": ["video"],
                },
            ]
        )
