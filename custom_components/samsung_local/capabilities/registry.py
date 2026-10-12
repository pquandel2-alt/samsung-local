"""Central capability engine."""

from __future__ import annotations

from typing import Any

from ..models import Capability, DeviceCategory
from .mappings import (
    KNOWN_RESOURCE_PATHS,
    map_common,
    map_course,
    map_operational,
    map_washer_settings,
)


class CapabilityRegistry:
    """Map live protocol resources into stable Home Assistant functions."""

    def discover(
        self,
        category: DeviceCategory,
        resources: dict[str, dict[str, Any]],
    ) -> tuple[dict[str, Capability], tuple[str, ...]]:
        """Return mapped capabilities and unhandled resource paths."""
        mapped = [*map_common(resources), *map_operational(resources)]
        if category in {DeviceCategory.WASHER, DeviceCategory.APPLIANCE, DeviceCategory.UNKNOWN}:
            mapped.extend(map_course(resources))
            mapped.extend(map_washer_settings(resources))
        capabilities: dict[str, Capability] = {}
        for capability in mapped:
            # Precedence is deterministic and standard OCF mappings are added first.
            capabilities.setdefault(capability.key, capability)
        unknown = tuple(sorted(set(resources) - KNOWN_RESOURCE_PATHS))
        return capabilities, unknown
