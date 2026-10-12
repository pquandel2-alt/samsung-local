"""Separate authentication management with no hidden runtime cloud access."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import StrEnum

from .certificates import (
    fetch_public_samsung_identity,
    mint_self_signed_client,
    normalize_pem,
    validate_certificate_pair,
)
from .tokens import normalize_psk


class OcfCredentialKind(StrEnum):
    CERTIFICATE = "certificate"
    PSK = "psk"


@dataclass(frozen=True, slots=True)
class OcfCredentials:
    """One mutually-exclusive OCF credential carrier."""

    kind: OcfCredentialKind
    certificate_pem: str | None = None
    private_key_pem: str | None = None
    psk_identity: str | None = None
    psk_key: str | None = None


class AuthenticationManager:
    """Create or validate credentials outside protocol adapters."""

    async def async_generate_ocf_credentials(
        self, public_identity: str | None = None
    ) -> OcfCredentials:
        """Create a certificate, fetching only a public UUID when omitted."""
        if public_identity is None:
            public_identity = await asyncio.to_thread(fetch_public_samsung_identity)
        certificate, key = await asyncio.to_thread(mint_self_signed_client, public_identity)
        return OcfCredentials(
            OcfCredentialKind.CERTIFICATE,
            certificate_pem=certificate,
            private_key_pem=key,
        )

    async def async_import_certificate(
        self, certificate_pem: str, private_key_pem: str
    ) -> OcfCredentials:
        """Validate imported certificate material without network access."""
        certificate_pem = normalize_pem(certificate_pem)
        private_key_pem = normalize_pem(private_key_pem)
        await asyncio.to_thread(validate_certificate_pair, certificate_pem, private_key_pem)
        return OcfCredentials(
            OcfCredentialKind.CERTIFICATE,
            certificate_pem=certificate_pem,
            private_key_pem=private_key_pem,
        )

    async def async_import_psk(self, identity: str, key: str) -> OcfCredentials:
        """Validate an already-authorized local OCF PSK."""
        normalized_identity, normalized_key = normalize_psk(identity, key)
        return OcfCredentials(
            OcfCredentialKind.PSK,
            psk_identity=normalized_identity,
            psk_key=normalized_key,
        )
