"""Keep pure unit tests runnable without installing Home Assistant Core."""

from __future__ import annotations

import sys
from enum import StrEnum
from importlib import import_module
from importlib.util import find_spec
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).parents[1]
PACKAGE_ROOT = REPOSITORY_ROOT / "custom_components" / "samsung_local"
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

# Importing a submodule normally executes the integration's Home Assistant
# entrypoint.  Pure protocol/model tests intentionally replace only that
# package object; CI's Home Assistant job does not use this bootstrap.
if find_spec("homeassistant") is None:
    package = ModuleType("custom_components.samsung_local")
    package.__path__ = [str(PACKAGE_ROOT)]  # type: ignore[attr-defined]
    sys.modules["custom_components.samsung_local"] = package
    parent_package = import_module("custom_components")
    parent_package.samsung_local = package  # type: ignore[attr-defined]
    homeassistant = ModuleType("homeassistant")
    ha_const = ModuleType("homeassistant.const")

    class Platform(StrEnum):
        MEDIA_PLAYER = "media_player"
        REMOTE = "remote"
        SENSOR = "sensor"
        BINARY_SENSOR = "binary_sensor"
        SWITCH = "switch"
        BUTTON = "button"
        SELECT = "select"
        NUMBER = "number"
        CLIMATE = "climate"
        FAN = "fan"

    ha_const.Platform = Platform  # type: ignore[attr-defined]
    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.const"] = ha_const
