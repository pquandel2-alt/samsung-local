"""Token validation helpers."""

from __future__ import annotations

import re

_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9._~+/=-]{1,4096}$")


def normalize_tv_token(token: str | None) -> str | None:
    """Reject control characters and unreasonable tokens before persistence."""
    if token is None or not token.strip():
        return None
    token = token.strip()
    if not _SAFE_TOKEN.fullmatch(token):
        raise ValueError("invalid TV token")
    return token


def normalize_psk(identity: str, key: str) -> tuple[str, str]:
    """Normalize a UUID identity and 16/32-byte hexadecimal PSK."""
    from uuid import UUID

    normalized_identity = str(UUID(identity.strip()))
    normalized_key = key.strip().lower().replace(":", "")
    if len(normalized_key) not in {32, 64} or not all(
        character in "0123456789abcdef" for character in normalized_key
    ):
        raise ValueError("PSK must contain 16 or 32 bytes of hexadecimal data")
    return normalized_identity, normalized_key
