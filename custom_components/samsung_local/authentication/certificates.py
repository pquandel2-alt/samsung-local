"""Certificate creation and validation for Samsung OCF devices."""

from __future__ import annotations

import re
import socket
import ssl
from datetime import UTC, datetime, timedelta
from uuid import UUID

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

SAMSUNG_PUBLIC_ID_HOST = "connect-v2.samsungiotcloud.com"


def normalize_pem(value: str) -> str:
    """Normalize pasted PEM without altering its encoded content."""
    value = value.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line for line in value.splitlines() if line.strip()) + "\n"


def validate_certificate_pair(certificate_pem: str, private_key_pem: str) -> None:
    """Validate that a PEM certificate and unencrypted key belong together."""
    certificate = x509.load_pem_x509_certificate(normalize_pem(certificate_pem).encode())
    key = serialization.load_pem_private_key(normalize_pem(private_key_pem).encode(), None)
    cert_public = certificate.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    key_public = key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    if cert_public != key_public:
        raise ValueError("certificate and private key do not match")


def fetch_public_samsung_identity() -> str:
    """Read the public UUID from Samsung's gateway certificate once.

    The gateway uses a chain unsuitable for normal Web PKI verification.  This
    narrowly-scoped connection only reads a public subject value; it sends no
    account, device, network, or Home Assistant data.  Runtime device control
    never calls this function.
    """
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    with (
        socket.create_connection((SAMSUNG_PUBLIC_ID_HOST, 443), timeout=15) as raw,
        context.wrap_socket(raw, server_hostname=SAMSUNG_PUBLIC_ID_HOST) as tls,
    ):
        certificate_der = tls.getpeercert(binary_form=True)
    if certificate_der is None:
        raise RuntimeError("Samsung gateway returned no certificate")
    certificate = x509.load_der_x509_certificate(certificate_der)
    for attribute in certificate.subject:
        if attribute.oid != NameOID.ORGANIZATIONAL_UNIT_NAME:
            continue
        match = re.search(r"uuid:([0-9a-f-]+)", str(attribute.value), re.IGNORECASE)
        if match:
            return str(UUID(match.group(1)))
    raise RuntimeError("Samsung gateway certificate contains no public UUID")


def mint_self_signed_client(identity: str) -> tuple[str, str]:
    """Mint the identity-shaped client certificate accepted by compatible OCF firmware."""
    identity = str(UUID(identity))
    subject = x509.Name(
        (
            x509.NameAttribute(NameOID.COUNTRY_NAME, "KR"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Samsung Electronics"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, f"uuid:{identity}"),
            x509.NameAttribute(NameOID.COMMON_NAME, f"urn:uuid:{identity}"),
        )
    )
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=3650))
        .sign(key, hashes.SHA256())
    )
    certificate_pem = certificate.public_bytes(serialization.Encoding.PEM).decode()
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    return certificate_pem, key_pem
