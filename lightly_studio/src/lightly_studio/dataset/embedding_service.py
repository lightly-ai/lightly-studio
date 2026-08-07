"""Contract helpers for customer-hosted embedding services.

An embedding service is an HTTP endpoint the customer runs on their own network that
implements the embedding wire contract (see ``docs/enterprise/custom_embedding_model.md``). The
browser calls it directly; the Lightly Studio backend only stores where it lives.
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

# Hostnames the browser treats as a secure context, so plain http is allowed for them.
_LOOPBACK_HOST_NAMES = frozenset({"localhost"})


def validate_serving_url(serving_url: str) -> str:
    """Validate and normalize the URL an embedding service is reachable at.

    Hosted Studio is served over HTTPS, so the browser blocks plain-http requests as
    mixed content. Rejecting them here surfaces the problem when an admin saves the URL
    instead of as an inscrutable error during a search.

    Args:
        serving_url: Base URL of the embedding service, e.g. ``https://gpu-box:8123``.

    Returns:
        The URL without a trailing slash.

    Raises:
        ValueError: If the URL has no host, or uses a scheme other than https on a
            non-loopback host.
    """
    parsed = urlparse(serving_url)
    if not parsed.hostname:
        raise ValueError(f"Embedding service URL '{serving_url}' has no host.")

    if parsed.scheme != "https" and not _is_loopback_host(parsed.hostname):
        raise ValueError(
            f"Embedding service URL '{serving_url}' must use https. Plain http is only "
            f"allowed for loopback hosts, because the browser blocks mixed content."
        )

    return serving_url.rstrip("/")


def _is_loopback_host(hostname: str) -> bool:
    if hostname in _LOOPBACK_HOST_NAMES:
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False
