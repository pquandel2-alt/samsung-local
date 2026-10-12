"""Evidence-driven Samsung OCF resource mappings.

The field names and semantics follow the public OCF representations observed
by LocalThings.  No entity is created from a model-name guess.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import Any

from ..models import Capability, DataType, EntityPlatform, WriteSpec

OPERATIONAL = "/operational/state/vs/0"
COURSE = "/course/vs/0"
WASHER = "/washer/vs/0"


def _duration_seconds(value: Any) -> int | None:
    if not isinstance(value, str):
        return None
    try:
        parts = [int(part) for part in value.split(":")]
    except ValueError:
        return None
    if len(parts) == 3:
        hours, minutes, seconds = parts
    elif len(parts) == 2:
        hours, (minutes, seconds) = 0, parts
    else:
        return None
    if min(hours, minutes, seconds) < 0:
        return None
    return hours * 3600 + minutes * 60 + seconds


def _number(value: Any, scale: float = 1.0) -> float | int | None:
    try:
        result = float(value) * scale
    except (TypeError, ValueError):
        return None
    return int(result) if result.is_integer() else result


def _option(options: Any, prefix: str) -> str | None:
    if not isinstance(options, (list, tuple)):
        return None
    marker = f"{prefix}_"
    for item in options:
        if isinstance(item, str) and item.startswith(marker):
            return item[len(marker) :]
    return None


def _course_codes(resources: dict[str, dict[str, Any]]) -> tuple[str, ...]:
    edit = (resources.get("/wm/editcourse/vs/0") or {}).get("x.com.samsung.da.editCourseList")
    if isinstance(edit, str) and "_" in edit:
        raw = edit.split("_", 1)[1]
        if len(raw) % 2 == 0 and raw:
            return tuple(raw[index : index + 2] for index in range(0, len(raw), 2))
    supported = (resources.get(COURSE) or {}).get("x.com.samsung.da.supportedOptions")
    values: list[str] = []
    if isinstance(supported, (list, tuple)):
        for item in supported:
            if isinstance(item, str) and item.startswith("Course_"):
                values.append(item.split("_", 1)[1])
    return tuple(dict.fromkeys(values))


def _cap(
    key: str,
    platform: EntityPlatform,
    value: Any,
    **kwargs: Any,
) -> Capability:
    return Capability(key=key, platform=platform, value=value, **kwargs)


def map_operational(resources: dict[str, dict[str, Any]]) -> list[Capability]:
    rep = resources.get(OPERATIONAL)
    if not rep:
        return []
    result: list[Capability] = []
    state_raw = rep.get("x.com.samsung.da.state")
    state_map = {
        "Ready": "idle",
        "Run": "active",
        "Running": "active",
        "Pause": "paused",
        "Paused": "paused",
        "End": "idle",
        "Stop": "idle",
    }
    state = state_map.get(str(state_raw), str(state_raw).lower()) if state_raw is not None else None
    if state_raw is not None:
        result.append(
            _cap(
                "machine_state",
                EntityPlatform.SENSOR,
                state,
                data_type=DataType.STRING,
                device_class="enum",
                options=("idle", "active", "paused"),
            )
        )
        progress_raw = rep.get("x.com.samsung.da.progress")
        running = state == "active" and progress_raw != "Finish"
        result.append(
            _cap(
                "cycle_active",
                EntityPlatform.BINARY_SENSOR,
                running,
                data_type=DataType.BOOLEAN,
                device_class="running",
            )
        )
        for key, payload, icon, allowed in (
            ("start", "Run", "mdi:play", ("idle", "paused")),
            ("pause", "Pause", "mdi:pause", ("active",)),
            ("stop", "Ready", "mdi:stop", ("active", "paused")),
        ):
            result.append(
                _cap(
                    key,
                    EntityPlatform.BUTTON,
                    None,
                    readable=False,
                    writable=True,
                    icon=icon,
                    write=WriteSpec(
                        command="ocf_write",
                        resource=OPERATIONAL,
                        field="x.com.samsung.da.state",
                        payload=payload,
                        requires_remote_control=key != "stop",
                        allowed_states=allowed,
                    ),
                )
            )
    if (progress := rep.get("x.com.samsung.da.progress")) is not None:
        result.append(_cap("program_progress", EntityPlatform.SENSOR, str(progress).lower()))
    if "x.com.samsung.da.progressPercentage" in rep:
        result.append(
            _cap(
                "program_progress_percentage",
                EntityPlatform.SENSOR,
                _number(rep.get("x.com.samsung.da.progressPercentage")),
                data_type=DataType.INTEGER,
                unit="%",
                state_class="measurement",
            )
        )
    seconds = _duration_seconds(rep.get("x.com.samsung.da.remainingTime", rep.get("remainingTime")))
    if seconds is not None:
        remaining = (
            0 if rep.get("x.com.samsung.da.progress") == "Finish" else math.ceil(seconds / 60)
        )
        result.append(
            _cap(
                "remaining_time",
                EntityPlatform.SENSOR,
                remaining,
                data_type=DataType.DURATION,
                unit="min",
                device_class="duration",
                state_class="measurement",
            )
        )
        finish = None
        if state == "active" and seconds > 0:
            finish = (datetime.now(UTC) + timedelta(seconds=seconds)).replace(
                second=0, microsecond=0
            )
        result.append(
            _cap(
                "estimated_finish",
                EntityPlatform.SENSOR,
                finish,
                data_type=DataType.DATETIME,
                device_class="timestamp",
            )
        )
    return result


def map_course(resources: dict[str, dict[str, Any]]) -> list[Capability]:
    rep = resources.get(COURSE)
    if not rep:
        return []
    options = rep.get("x.com.samsung.da.options")
    current = _option(options, "Course")
    available = _course_codes(resources)
    if current is None and not available:
        return []
    if current and current not in available:
        available = (*available, current)
    return [
        _cap(
            "program",
            EntityPlatform.SELECT,
            current,
            writable=bool(available and isinstance(options, (list, tuple))),
            options=available,
            icon="mdi:washing-machine",
            write=(
                WriteSpec(
                    command="ocf_option_write",
                    resource=COURSE,
                    field="x.com.samsung.da.options",
                    requires_remote_control=True,
                )
                if available and isinstance(options, (list, tuple))
                else None
            ),
            attributes={"values_are_device_codes": True},
        )
    ]


def map_washer_settings(resources: dict[str, dict[str, Any]]) -> list[Capability]:
    rep = resources.get(WASHER)
    if rep is None:
        return []
    result: list[Capability] = []
    fields = (
        ("temperature", "waterTemperature", "supportedWaterTemperature", "°C"),
        ("spin_speed", "spinLevel", "supportedSpinLevel", None),
        ("rinse_count", "rinseCycles", "supportedRinseCycles", None),
        ("soil_level", "soilLevel", "supportedSoilLevel", None),
    )
    for key, short_field, supported_field, unit in fields:
        field = f"x.com.samsung.da.{short_field}"
        supported = f"x.com.samsung.da.{supported_field}"
        if field not in rep and supported not in rep:
            continue
        values = rep.get(supported) or ()
        options = tuple(str(value) for value in values) if isinstance(values, (list, tuple)) else ()
        result.append(
            _cap(
                key,
                EntityPlatform.SELECT,
                None if rep.get(field) is None else str(rep.get(field)),
                writable=bool(options),
                options=options,
                unit=unit,
                entity_category="config",
                write=(
                    WriteSpec(
                        command="ocf_write",
                        resource=WASHER,
                        field=field,
                        requires_remote_control=True,
                    )
                    if options
                    else None
                ),
            )
        )
    return result


def map_common(resources: dict[str, dict[str, Any]]) -> list[Capability]:
    result: list[Capability] = []
    power = resources.get("/power/0")
    power_href, power_field, power_value = "/power/0", "value", None
    if power is not None and "value" in power:
        power_value = bool(power["value"])
    elif (power := resources.get("/power/vs/0")) is not None:
        power_href = "/power/vs/0"
        power_field = "x.com.samsung.da.power"
        if power_field in power:
            power_value = str(power[power_field]).lower() == "on"
    if power_value is not None:
        setting = resources.get("/wm/setinfo/vs/0") or {}
        allows_write = (
            str(setting.get("x.com.samsung.da.isModelSettingPowerOnOff", "false")).lower() == "true"
        )
        result.append(
            _cap(
                "power",
                EntityPlatform.SWITCH if allows_write else EntityPlatform.BINARY_SENSOR,
                power_value,
                data_type=DataType.BOOLEAN,
                writable=allows_write,
                device_class=None if allows_write else "power",
                write=(
                    WriteSpec(command="ocf_write", resource=power_href, field=power_field)
                    if allows_write
                    else None
                ),
            )
        )
    remote = resources.get("/remotectrl/0")
    if remote is not None and "value" in remote:
        remote_value: bool | None = bool(remote["value"])
    else:
        remote = resources.get("/remotectrl/vs/0")
        remote_value = (
            str(remote.get("x.com.samsung.da.remoteControlEnabled", "")).lower() == "true"
            if remote is not None
            else None
        )
    if remote_value is not None:
        result.append(
            _cap(
                "remote_control_enabled",
                EntityPlatform.BINARY_SENSOR,
                remote_value,
                data_type=DataType.BOOLEAN,
                device_class="connectivity",
            )
        )
    kids = resources.get("/kidslock/0")
    if kids is not None and "value" in kids:
        locked: bool | None = bool(kids["value"])
    else:
        kids = resources.get("/kidslock/vs/0")
        locked = (
            str(kids.get("x.com.samsung.da.kidsLock", "")) != "Ready" if kids is not None else None
        )
    if locked is not None:
        result.append(
            _cap(
                "child_lock",
                EntityPlatform.BINARY_SENSOR,
                locked,
                data_type=DataType.BOOLEAN,
                device_class="lock",
            )
        )
    alarms = resources.get("/alarms/vs/0")
    if alarms is not None and "x.com.samsung.da.items" in alarms:
        active: list[str] = []
        for item in alarms.get("x.com.samsung.da.items") or []:
            if not isinstance(item, dict):
                continue
            code = item.get("x.com.samsung.da.errorCode") or item.get("errorCode")
            alarm_status = str(item.get("x.com.samsung.da.status", item.get("status", ""))).lower()
            if code and alarm_status not in {"normal", "inactive", "off", "false", "0"}:
                active.append(str(code))
        result.append(
            _cap(
                "error_code",
                EntityPlatform.SENSOR,
                ", ".join(active) if active else "none",
                entity_category="diagnostic",
                icon="mdi:alert",
            )
        )
    energy = resources.get("/energy/consumption/vs/0")
    if energy:
        if (raw := energy.get("x.com.samsung.da.instantaneousPower")) not in (None, "-500"):
            result.append(
                _cap(
                    "power_consumption",
                    EntityPlatform.SENSOR,
                    _number(raw),
                    data_type=DataType.FLOAT,
                    unit="W",
                    device_class="power",
                    state_class="measurement",
                )
            )
        if "x.com.samsung.da.cumulativePower" in energy:
            result.append(
                _cap(
                    "energy_consumption",
                    EntityPlatform.SENSOR,
                    _number(energy.get("x.com.samsung.da.cumulativePower"), 0.001),
                    data_type=DataType.FLOAT,
                    unit="kWh",
                    device_class="energy",
                    state_class="total_increasing",
                )
            )
    job_status = resources.get("/wm/jobbeginingstatus/vs/0")
    if job_status and "x.com.samsung.da.currentStatus" in job_status:
        result.append(
            _cap(
                "job_beginning_status",
                EntityPlatform.SENSOR,
                job_status.get("x.com.samsung.da.currentStatus"),
                entity_category="diagnostic",
            )
        )
    return result


KNOWN_RESOURCE_PATHS = frozenset(
    {
        OPERATIONAL,
        COURSE,
        WASHER,
        "/wm/editcourse/vs/0",
        "/st/washercourse/vs/0",
        "/power/0",
        "/power/vs/0",
        "/remotectrl/0",
        "/remotectrl/vs/0",
        "/kidslock/0",
        "/kidslock/vs/0",
        "/alarms/vs/0",
        "/energy/consumption/vs/0",
        "/wm/jobbeginingstatus/vs/0",
        "/wm/setinfo/vs/0",
        "/information/vs/0",
        "/wirelessinfo/vs/0",
    }
)
