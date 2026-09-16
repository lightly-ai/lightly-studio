"""The address policy of ``RemoteEmbedder``.

LightlyStudio opens a connection to an address that a user gives it. Without a check, that
address can name the loopback interface of our own host, a machine inside our own network,
or the metadata endpoint of the cloud that runs us. The two functions here are the control
against that reach.

``LIGHTLY_STUDIO_REMOTE_EMBEDDER_ALLOW_PRIVATE_URLS`` chooses the mode. It is ``True`` by
default, because a self-hosted LightlyStudio and its model usually share a box or a
private network, and such an address is then the normal one. A hosted deployment, where
the address arrives from a user, sets it to ``False``.

A refused address raises ``ValueError``, not a ``RemoteEmbedderError``. Nothing was sent
and no server answered: the configuration is wrong, so no retry and no other server helps.
"""

from __future__ import annotations

import ipaddress
import socket
import warnings
from urllib.parse import SplitResult, urlsplit

import httpx

from lightly_studio.dataset import env

_HTTPS_SCHEME = "https"

# A port on this name is out of reach for other hosts. Only `localhost` is listed, because
# any other name is not an address. A name that does resolve to loopback then gets a
# warning that it does not need, which is the safe side of the two.
_LOOPBACK_HOST_NAME = "localhost"


def check_url(url: str, api_key: str | None) -> None:
    """Check the address of an embedding server against the policy.

    The strict mode refuses an address that reaches this host or this network. The
    permissive mode allows it and only warns about a plain HTTP address that other hosts
    can reach.

    Args:
        url: The address of the server, the one that requests really go to.
        api_key: The token that the client sends, or ``None`` for a server that wants
            none. Only the warning reads it.

    Raises:
        ValueError: If ``url`` is not a usable address, or if the strict mode refuses it.
    """
    parsed = urlsplit(url)
    if not parsed.scheme or not parsed.hostname:
        raise ValueError(
            f"{url!r} is not a usable address for an embedding server. Give a scheme and a "
            f"host, such as 'https://models.example.com:8080'."
        )
    if not env.LIGHTLY_STUDIO_REMOTE_EMBEDDER_ALLOW_PRIVATE_URLS:
        _check_public(parsed=parsed)
    _warn_on_clear_text(parsed=parsed, api_key=api_key)


def check_no_redirects(client: httpx.Client) -> None:
    """Refuse a client that follows a redirect.

    ``False`` is the default of ``httpx.Client``, but it is not the default everywhere:
    ``fastapi.testclient.TestClient`` follows redirects. The value is therefore checked
    and not assumed, for a client that a caller passes in as much as for the one that
    ``connect`` opens. A redirect would carry the batch, and the bearer token with it, to
    an address that nobody configured, which is the same reach that ``check_url`` closes.

    Args:
        client: The client that carries the requests.

    Raises:
        ValueError: If ``client`` follows redirects.
    """
    if client.follow_redirects:
        raise ValueError(
            "The client of a remote embedder must not follow redirects. A redirect would "
            "send the batch, and the bearer token with it, to an address that nobody "
            "configured. Build the client with follow_redirects=False."
        )


def _check_public(parsed: SplitResult) -> None:
    """Refuse what the strict mode refuses: plain HTTP, and a host inside this network.

    Args:
        parsed: The address of the server.

    Raises:
        ValueError: If the scheme is not ``https``, or if the host reaches an address that
            is not public.
    """
    if parsed.scheme != _HTTPS_SCHEME:
        raise ValueError(
            f"{parsed.geturl()!r} is not https. "
            f"LIGHTLY_STUDIO_REMOTE_EMBEDDER_ALLOW_PRIVATE_URLS is false, so an embedding "
            f"server must be reached over TLS."
        )
    host = parsed.hostname
    assert host is not None
    # The addresses are read here, once, when the embedder is built. A name that answers
    # with another address afterwards is out of reach of this check. The ban on redirects
    # and the single read of `/v1/describe` are what keep that window small.
    for address in _resolved_addresses(host=host):
        _check_public_address(address=address, host=host)


def _resolved_addresses(host: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """Every address that ``host`` names.

    Args:
        host: An address literal, or a name to resolve.

    Returns:
        The address itself for a literal. For a name, every address of every record it
        carries, because one name can answer with more than one.

    Raises:
        ValueError: If ``host`` is a name that does not resolve.
    """
    try:
        return [ipaddress.ip_address(host)]
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        raise ValueError(
            f"The host {host!r} of the embedding server does not resolve: {error}"
        ) from error
    # An IPv6 address can carry a zone, such as `fe80::1%eth0`, which is not part of it.
    return [ipaddress.ip_address(str(info[4][0]).partition("%")[0]) for info in infos]


def _check_public_address(
    address: ipaddress.IPv4Address | ipaddress.IPv6Address, host: str
) -> None:
    """Refuse an address that names this host, this network, or the metadata endpoint.

    ``169.254.169.254`` is the reason this control exists: it is link-local, it answers on
    most clouds, and it hands out the credentials of the instance to whoever asks.

    Args:
        address: One address that ``host`` resolves to.
        host: The host of the URL, for the message.

    Raises:
        ValueError: If the address is not a public one.
    """
    if not _reaches_this_network(address=address):
        return
    raise ValueError(
        f"The host {host!r} of the embedding server resolves to {address}, which is not a "
        f"public address. LIGHTLY_STUDIO_REMOTE_EMBEDDER_ALLOW_PRIVATE_URLS is false, so an "
        f"embedding server must not be reachable from inside this network."
    )


def _reaches_this_network(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Whether an address stays on this host or inside this network.

    The ranges overlap: a link-local address is also a private one. They are listed one by
    one so that a reader sees what the check covers.
    """
    return (
        address.is_loopback
        or address.is_private
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
    )


def _warn_on_clear_text(parsed: SplitResult, api_key: str | None) -> None:
    """Name every risk of an address that carries the batches in the clear.

    The twin of ``_warn_public_bind`` in ``lightly_studio_serve.server``: that one warns
    the host that serves the model, this one warns the host that calls it, and each names
    every risk rather than the first one. A loopback address needs neither warning,
    because no other host can reach the port.

    Plain HTTP with a token is the worse of the two cases, not the safer one: the token is
    reusable, it goes out with every request, and any host on the path reads it.
    """
    if parsed.scheme == _HTTPS_SCHEME or _is_loopback(parsed=parsed):
        return
    address = parsed.geturl()
    risks = [
        f"Calling the embedding server at {address} over plain HTTP. The batches, and the "
        f"vectors that come back, go over the network in clear text."
    ]
    if api_key is None:
        risks.append("No api_key is set, so every host that can reach the port can use the model.")
    else:
        risks.append(
            "The bearer token goes with every request, so any host on the path can read it "
            "and reuse it."
        )
    risks.append(
        "Give an https address, end TLS at a proxy in front of the server, or serve the "
        "model on a loopback address."
    )
    warnings.warn(" ".join(risks), stacklevel=4)


def _is_loopback(parsed: SplitResult) -> bool:
    """Whether a port on the host of this address is out of reach for other hosts."""
    host = parsed.hostname
    if host is None:
        return False
    if host == _LOOPBACK_HOST_NAME:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False
