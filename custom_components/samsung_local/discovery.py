"""Bounded discovery for known Samsung local endpoints."""

from __future__ import annotations

import asyncio
import socket
from functools import partial
from types import MappingProxyType
from urllib.parse import urlparse

import aiohttp
from smartthings_local.protocol.dtls_probe import probe_dtls_ports

from .const import LEGACY_PORT, OCF_FALLBACK_PORT, OCF_PORTS, REQUEST_TIMEOUT, TIZEN_PORTS
from .models import DeviceCategory, DiscoveryResult, Protocol


def _valid_host(host: str) -> str:
    host = host.strip()
    if not host or any(character in host for character in "/?#@"):
        raise ValueError("host must be a single IP address or hostname")
    return host


async def _tv_probe(session: aiohttp.ClientSession, host: str, port: int) -> DiscoveryResult | None:
    scheme = "https" if port == 8002 else "http"
    url = f"{scheme}://{host}:{port}/api/v2/"
    try:
        async with asyncio.timeout(REQUEST_TIMEOUT):
            async with session.get(url, ssl=scheme != "https") as response:
                if response.status != 200:
                    return None
                payload = await response.json(content_type=None)
    except (TimeoutError, aiohttp.ClientError, ValueError, OSError):
        return None
    device = payload.get("device") if isinstance(payload, dict) else None
    if not isinstance(device, dict):
        return None
    manufacturer = str(device.get("type", "") or payload.get("type", ""))
    model = device.get("modelName")
    if "samsung" not in str(payload).lower() and model is None and manufacturer:
        return None
    return DiscoveryResult(
        host=host,
        protocol=Protocol.TIZEN,
        port=port,
        name=str(device.get("name") or payload.get("name") or "Samsung TV"),
        model=str(model) if model else None,
        device_id=str(device.get("id") or payload.get("id"))
        if device.get("id") or payload.get("id")
        else None,
        category=DeviceCategory.TV,
        authentication_required=True,
        raw=MappingProxyType({"device": device}),
    )


def _tcp_open(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


async def async_discover_host(
    session: aiohttp.ClientSession,
    host: str,
    *,
    preferred_protocol: Protocol | None = None,
) -> list[DiscoveryResult]:
    """Probe one user/discovery supplied host; never scan an address range."""
    host = _valid_host(host)
    results: list[DiscoveryResult] = []
    if preferred_protocol in (None, Protocol.TIZEN):
        tv_results = await asyncio.gather(*(_tv_probe(session, host, port) for port in TIZEN_PORTS))
        if tv := next((result for result in tv_results if result is not None), None):
            results.append(tv)
            if preferred_protocol is Protocol.TIZEN:
                return results
    if preferred_protocol in (None, Protocol.LEGACY):
        if await asyncio.to_thread(_tcp_open, host, LEGACY_PORT):
            results.append(
                DiscoveryResult(
                    host=host,
                    protocol=Protocol.LEGACY,
                    port=LEGACY_PORT,
                    name="Samsung legacy appliance",
                    category=DeviceCategory.APPLIANCE,
                    authentication_required=True,
                )
            )
            if preferred_protocol is Protocol.LEGACY:
                return results
    if preferred_protocol in (None, Protocol.OCF):
        ports = (*OCF_PORTS, OCF_FALLBACK_PORT)
        try:
            probe = await asyncio.to_thread(
                partial(
                    probe_dtls_ports,
                    host,
                    ports,
                    timeout=1.5,
                    retries=1,
                )
            )
        except (OSError, ValueError):
            probe = None
        if probe is not None and probe.selected_port is not None:
            results.append(
                DiscoveryResult(
                    host=host,
                    protocol=Protocol.OCF,
                    port=probe.selected_port,
                    name="Samsung OCF appliance",
                    category=DeviceCategory.APPLIANCE,
                    authentication_required=True,
                    raw=MappingProxyType(
                        {
                            "probe_outcome": probe.outcome,
                            "responding_ports": tuple(probe.responder_ports),
                        }
                    ),
                )
            )
    return results


def host_from_discovery_url(url: str) -> str | None:
    """Extract only the host portion of an SSDP location."""
    try:
        return urlparse(url).hostname
    except ValueError:
        return None
