"""Bounded exponential reconnect policy."""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BackoffPolicy:
    """Exponential backoff with bounded symmetric jitter."""

    base: float = 2.0
    maximum: float = 300.0
    jitter: float = 0.2

    def delay(self, attempt: int, random_value: float | None = None) -> float:
        """Return a bounded delay; attempt zero is the first retry."""
        raw = min(self.maximum, self.base * float(2 ** max(attempt, 0)))
        sample = random.random() if random_value is None else random_value
        factor = 1 + ((sample * 2) - 1) * self.jitter
        return max(0.0, min(self.maximum, raw * factor))
