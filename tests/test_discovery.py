from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.samsung_local.discovery import _valid_host, host_from_discovery_url


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("http://192.0.2.10:9197/dmr", "192.0.2.10"),
        ("https://tv.local:8002/api/v2/", "tv.local"),
        ("not a url", None),
    ],
)
def test_ssdp_location_extracts_only_one_host(url: str, expected: str | None) -> None:
    assert host_from_discovery_url(url) == expected


@pytest.mark.parametrize("host", ["", "192.0.2.0/24", "tv.local/path", "user@host"])
def test_manual_discovery_rejects_ranges_and_urls(host: str) -> None:
    with pytest.raises(ValueError):
        _valid_host(host)


def test_manual_discovery_accepts_single_host() -> None:
    assert _valid_host(" 192.0.2.20 ") == "192.0.2.20"


def test_ssdp_manufacturer_matchers_are_service_scoped() -> None:
    manifest = json.loads(
        (Path(__file__).parents[1] / "custom_components/samsung_local/manifest.json").read_text()
    )
    for matcher in manifest["ssdp"]:
        if "manufacturer" in matcher:
            assert matcher["st"] == "urn:schemas-upnp-org:service:RenderingControl:1"
