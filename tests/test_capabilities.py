from __future__ import annotations

import json
from pathlib import Path

from custom_components.samsung_local.capabilities.registry import CapabilityRegistry
from custom_components.samsung_local.capabilities.validation import remote_control_is_enabled
from custom_components.samsung_local.models import DeviceCategory, EntityPlatform


def fixture(name: str):
    return json.loads((Path(__file__).parent / "fixtures" / name).read_text())


def test_washer_capabilities_are_derived_from_live_fields() -> None:
    resources = fixture("washer_ww90t554aae.json")["resources"]
    capabilities, unknown = CapabilityRegistry().discover(DeviceCategory.WASHER, resources)
    assert not unknown
    assert capabilities["machine_state"].value == "active"
    assert capabilities["program"].options == ("1C", "1D")
    assert capabilities["program"].writable is True
    assert capabilities["temperature"].options == ("20", "30", "40", "60")
    assert capabilities["remaining_time"].value == 42
    assert capabilities["estimated_finish"].value is not None
    assert capabilities["energy_consumption"].value == 12.345
    assert capabilities["start"].platform is EntityPlatform.BUTTON


def test_missing_fields_never_create_phantom_entities() -> None:
    capabilities, unknown = CapabilityRegistry().discover(
        DeviceCategory.WASHER,
        {"/washer/vs/0": {}, "/vendor/new/vs/0": {"mystery": True}},
    )
    assert capabilities == {}
    assert unknown == ("/vendor/new/vs/0",)


def test_firmware_capability_add_and_remove_is_deterministic() -> None:
    registry = CapabilityRegistry()
    before, _ = registry.discover(DeviceCategory.WASHER, {"/power/0": {"value": True}})
    after, _ = registry.discover(
        DeviceCategory.WASHER,
        {
            "/power/0": {"value": True},
            "/washer/vs/0": {
                "x.com.samsung.da.spinLevel": "800",
                "x.com.samsung.da.supportedSpinLevel": ["0", "800"],
            },
        },
    )
    removed, _ = registry.discover(DeviceCategory.WASHER, {"/power/0": {"value": True}})
    assert "spin_speed" not in before
    assert after["spin_speed"].writable
    assert "spin_speed" not in removed


def test_unknown_remote_control_state_is_never_treated_as_consent() -> None:
    assert remote_control_is_enabled({}) is False
    assert remote_control_is_enabled({"/remotectrl/0": {"value": True}}) is True


def test_power_write_requires_explicit_device_evidence() -> None:
    registry = CapabilityRegistry()
    read_only, _ = registry.discover(DeviceCategory.WASHER, {"/power/0": {"value": True}})
    writable, _ = registry.discover(
        DeviceCategory.WASHER,
        {
            "/power/0": {"value": True},
            "/wm/setinfo/vs/0": {"x.com.samsung.da.isModelSettingPowerOnOff": "true"},
        },
    )
    assert read_only["power"].platform is EntityPlatform.BINARY_SENSOR
    assert not read_only["power"].writable
    assert writable["power"].platform is EntityPlatform.SWITCH
    assert writable["power"].writable
