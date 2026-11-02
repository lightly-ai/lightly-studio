"""Helpers to create a private certificate authority for TLS tests."""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID


@dataclass
class CertificateWithKey:
    """A certificate and its private key."""

    certificate: x509.Certificate
    key: ec.EllipticCurvePrivateKey

    def certificate_pem(self) -> str:
        """Return the certificate as PEM text."""
        return self.certificate.public_bytes(serialization.Encoding.PEM).decode()

    def key_pem(self) -> str:
        """Return the private key as unencrypted PEM text."""
        return self.key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()


def create_ca(common_name: str, issuer: CertificateWithKey | None = None) -> CertificateWithKey:
    """Create a CA certificate. Without an issuer, the certificate is self-signed."""
    key = ec.generate_private_key(curve=ec.SECP256R1())
    builder = _builder(common_name=common_name, key=key, issuer=issuer).add_extension(
        x509.BasicConstraints(ca=True, path_length=None), critical=True
    )
    signing_key = key if issuer is None else issuer.key
    return CertificateWithKey(
        certificate=builder.sign(private_key=signing_key, algorithm=hashes.SHA256()), key=key
    )


def create_server_certificate(issuer: CertificateWithKey, host: str) -> CertificateWithKey:
    """Create a server certificate for a DNS name, issued by a CA."""
    key = ec.generate_private_key(curve=ec.SECP256R1())
    builder = (
        _builder(common_name=host, key=key, issuer=issuer)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName(host), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
            ),
            critical=False,
        )
    )
    return CertificateWithKey(
        certificate=builder.sign(private_key=issuer.key, algorithm=hashes.SHA256()), key=key
    )


def _builder(
    common_name: str, key: ec.EllipticCurvePrivateKey, issuer: CertificateWithKey | None
) -> x509.CertificateBuilder:
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = datetime.now(tz=timezone.utc)
    return (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name if issuer is None else issuer.certificate.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=30))
    )
