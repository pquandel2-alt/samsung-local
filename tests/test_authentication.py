from __future__ import annotations

import pytest

from custom_components.samsung_local.authentication.certificates import (
    mint_self_signed_client,
    validate_certificate_pair,
)
from custom_components.samsung_local.authentication.tokens import normalize_psk, normalize_tv_token


def test_minted_certificate_and_key_match() -> None:
    certificate, key = mint_self_signed_client("11111111-2222-3333-4444-555555555555")
    validate_certificate_pair(certificate, key)
    assert "BEGIN CERTIFICATE" in certificate
    assert "PRIVATE KEY" in key


def test_invalid_psk_is_rejected() -> None:
    with pytest.raises(ValueError):
        normalize_psk("11111111-2222-3333-4444-555555555555", "not-a-key")


def test_token_rejects_control_characters() -> None:
    with pytest.raises(ValueError):
        normalize_tv_token("secret\nleak")
