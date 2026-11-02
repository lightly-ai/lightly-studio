"""CA bundle files that add custom CA certificates to the default trust store.

HTTP clients such as botocore read a CA bundle path from an environment variable, for
example ``AWS_CA_BUNDLE``. The file replaces the default trust store, so the file written
here contains the default CA bundle followed by the custom certificates. Public HTTPS
endpoints thus stay trusted.
"""

from __future__ import annotations

import atexit
import os
import re
import tempfile
from contextlib import suppress
from ssl import PROTOCOL_TLS_CLIENT, SSLContext, SSLError

MAX_CA_BUNDLE_PEM_BYTES = 64 * 1024

_CERTIFICATE_PATTERN = re.compile(
    r"-----BEGIN CERTIFICATE-----[A-Za-z0-9+/=\s]+-----END CERTIFICATE-----"
)

# Paths of the CA bundle files written by this process.
_written_files: list[str] = []


def write_ca_bundle(pem: str) -> str:
    """Validate custom CA certificates and write them to a private CA bundle file.

    The file contains the default CA bundle followed by the custom certificates.

    Args:
        pem: One or more PEM-encoded X.509 certificates.

    Returns:
        The path of the CA bundle file.

    Raises:
        ValueError: If the PEM text is too large, contains a private key, or contains no
            valid certificate.
    """
    certificates = _validate_pem(pem=pem)
    content = f"{_read_default_ca_bundle().rstrip()}\n{certificates}"
    file_descriptor, path = tempfile.mkstemp(prefix="lightly-studio-ca-", suffix=".pem")
    # Track the file before the write, so that delete_ca_bundles also removes it if the
    # write fails.
    _written_files.append(path)
    with os.fdopen(file_descriptor, "w", encoding="utf-8") as file:
        file.write(content)
    return path


def delete_ca_bundles(keep: str | None) -> None:
    """Delete all CA bundle files written by this process, except one.

    Args:
        keep: The path of the file to keep, or None to delete all files.
    """
    for path in [path for path in _written_files if path != keep]:
        with suppress(FileNotFoundError):
            os.remove(path)
        _written_files.remove(path)


def _validate_pem(pem: str) -> str:
    """Return the certificate blocks of the PEM text, separated by newlines."""
    if len(pem.encode()) > MAX_CA_BUNDLE_PEM_BYTES:
        raise ValueError(
            f"The CA bundle is larger than {MAX_CA_BUNDLE_PEM_BYTES // 1024} KiB. "
            "Use only the CA certificates of your organization, not a full system bundle."
        )
    if "PRIVATE KEY" in pem:
        raise ValueError("The CA bundle contains a private key. Use only certificates.")

    certificates = _CERTIFICATE_PATTERN.findall(pem)
    if not certificates:
        raise ValueError("The CA bundle contains no PEM certificate.")

    joined = "\n".join(certificates) + "\n"
    try:
        SSLContext(PROTOCOL_TLS_CLIENT).load_verify_locations(cadata=joined)
    except SSLError as error:
        raise ValueError("The CA bundle contains an invalid certificate.") from error
    return joined


def _read_default_ca_bundle() -> str:
    # certifi is part of the cloud-storage extra. Import it only when a custom CA bundle
    # is written.
    import certifi  # noqa: PLC0415

    requests_ca_bundle = os.environ.get("REQUESTS_CA_BUNDLE")
    path = (
        requests_ca_bundle
        if requests_ca_bundle and os.path.isfile(requests_ca_bundle)
        else certifi.where()
    )
    with open(path, encoding="utf-8") as file:
        return file.read()


atexit.register(delete_ca_bundles, keep=None)
