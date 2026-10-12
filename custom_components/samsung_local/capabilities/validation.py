"""Validation helpers used before protocol writes."""

from __future__ import annotations

from typing import Any

from ..exceptions import InvalidCommandError
from ..models import Capability


def validate_capability_value(capability: Capability, value: Any) -> Any:
    """Validate a writable capability value and return its normalized form."""
    if not capability.writable or capability.write is None:
        raise InvalidCommandError(f"{capability.key} is read-only")
    if capability.options:
        normalized = str(value)
        if normalized not in capability.options:
            raise InvalidCommandError(
                f"{normalized!r} is not a supported value for {capability.key}"
            )
        return normalized
    if capability.native_min is not None or capability.native_max is not None:
        try:
            normalized_number = float(value)
        except (TypeError, ValueError) as err:
            raise InvalidCommandError(f"{capability.key} requires a number") from err
        if capability.native_min is not None and normalized_number < capability.native_min:
            raise InvalidCommandError(f"{capability.key} is below its minimum")
        if capability.native_max is not None and normalized_number > capability.native_max:
            raise InvalidCommandError(f"{capability.key} is above its maximum")
        return normalized_number
    return value


def remote_control_is_enabled(resources: dict[str, dict[str, Any]]) -> bool:
    """Read Samsung's two known Smart Control resource variants."""
    if (generic := resources.get("/remotectrl/0")) is not None:
        return bool(generic.get("value"))
    if (vendor := resources.get("/remotectrl/vs/0")) is not None:
        return str(vendor.get("x.com.samsung.da.remoteControlEnabled", "")).lower() == "true"
    # Absence is not consent.  A user can explicitly override this conservative
    # default in the per-device options when hardware evidence justifies it.
    return False
