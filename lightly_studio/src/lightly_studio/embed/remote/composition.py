"""Builds the class that carries exactly the capabilities that a server advertises.

A remote embedder is not a fixed class list. ``/v1/describe`` names what the server serves,
and this module composes a class out of the route classes for those capabilities, so the
``isinstance`` dispatch of ``EmbedderRegistry`` keeps working.

The caller passes the route classes that it can serve, one per capability. This module
composes the class and refuses a server that LightlyStudio can never ask for an embedding.
"""

from __future__ import annotations

import functools
from collections.abc import Mapping, Sequence

from lightly_studio_serve.embedder import Capability, Embedder

from lightly_studio.embed.remote.errors import RemoteEmbedderCapabilityError

# The capabilities that `EmbedderRegistry` can hand back. Its `_CAPABILITY_TO_TYPE` has no
# `VIDEO_BYTES` entry, so a video-only server gives an embedder that nothing in
# LightlyStudio ever asks for, and `register` refuses it with "implements no capability".
# TODO(Iunir, 09/2026): Remove this constant when the registry gains a `VIDEO_BYTES` entry.
_RESOLVABLE_CAPABILITIES = (Capability.TEXT, Capability.IMAGE_BYTES)


def compose_remote_embedder_class(
    capabilities: Sequence[Capability],
    capability_to_base: Mapping[Capability, type[Embedder]],
) -> type[Embedder]:
    """Build the embedder class for the capabilities that one server advertises.

    Args:
        capabilities: The capabilities that ``/v1/describe`` reported, in wire order.
        capability_to_base: The route class that serves each capability the client routes
            to, in a fixed order. A capability that is absent is ignored, never assumed
            routable. The order is the order of the bases, so two servers that advertise
            the same set compose the same class.

    Returns:
        A class that implements the interface of every advertised capability that the
        client routes to, and that ``isinstance`` reports as each of its route classes.

    Raises:
        RemoteEmbedderCapabilityError: If nothing advertised is routable, or if the only
            routable capabilities are ones that ``EmbedderRegistry`` cannot resolve.
    """
    advertised = set(capabilities)
    routable = tuple(capability for capability in capability_to_base if capability in advertised)
    _check_routable(advertised=capabilities, routable=routable, routes_to=tuple(capability_to_base))
    return _composed_class(bases=tuple(capability_to_base[capability] for capability in routable))


@functools.cache
def _composed_class(bases: tuple[type[Embedder], ...]) -> type[Embedder]:
    """Build and cache the class that carries exactly ``bases``.

    Every base carries its own concrete methods, so the result has nothing abstract left.
    The classes are cached, because a new one for every call would stay for the life of
    the process. The name reads back the composed capabilities, for a repr and a traceback.

    Args:
        bases: The route classes to compose, in a fixed order.

    Returns:
        A class that ``isinstance`` reports as each of ``bases``.
    """
    capabilities = "".join(base.__name__.removeprefix("_").removesuffix("Route") for base in bases)
    return type(f"Remote{capabilities}Embedder", bases, {})


def _check_routable(
    advertised: Sequence[Capability],
    routable: Sequence[Capability],
    routes_to: Sequence[Capability],
) -> None:
    """Refuse a server that LightlyStudio can never ask for an embedding.

    Both errors arrive at construction, where the message can still name the real problem.
    Later, inside ``EmbedderRegistry.register``, the second one reads "implements no
    capability", which names the symptom instead.

    Args:
        advertised: The capabilities that ``/v1/describe`` reported.
        routable: The advertised capabilities that the client routes to.
        routes_to: Every capability that the client routes to.

    Raises:
        RemoteEmbedderCapabilityError: If nothing advertised is routable, or if the only
            routable capabilities are ones that the registry cannot resolve.
    """
    if not routable:
        raise RemoteEmbedderCapabilityError(
            f"The embedding server advertises {_names(capabilities=advertised)}. This client "
            f"routes to {_names(capabilities=routes_to)}."
        )
    if not set(routable) & set(_RESOLVABLE_CAPABILITIES):
        raise RemoteEmbedderCapabilityError(
            f"The embedding server advertises {_names(capabilities=advertised)}, of which "
            f"this client routes to {_names(capabilities=routable)}. EmbedderRegistry "
            f"resolves {_names(capabilities=_RESOLVABLE_CAPABILITIES)}, so nothing in "
            f"LightlyStudio would ask this embedder for a vector."
        )


def _names(capabilities: Sequence[Capability]) -> str:
    """Name capabilities the way the wire writes them, for a message.

    A capability is named once: ``DescribeResponse`` validates no uniqueness.
    """
    return ", ".join(dict.fromkeys(capability.value for capability in capabilities))
