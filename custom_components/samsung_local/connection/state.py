"""Mutable connection telemetry kept out of immutable device snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..models import ConnectionStatus


@dataclass(slots=True)
class ConnectionTelemetry:
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    reconnect_attempt: int = 0
    last_connected: datetime | None = None
    last_error: str | None = None
