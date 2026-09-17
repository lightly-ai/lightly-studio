"""Builds the class that carries exactly the capabilities that a server advertises.

A remote embedder is not a fixed class list. ``/v1/describe`` names what the server serves,
and the client composes a class out of the interfaces for those capabilities, so the
``isinstance`` dispatch of ``EmbedderRegistry`` keeps working.

This module holds the mechanism only. Which capabilities a client routes to, and which
ones the registry can resolve, are policy that the caller passes in.
"""

from __future__ import annotations

import functools
from collections.abc import Sequence

from lightly_studio_serve.embedder import Capability, Embedder

from lightly_studio.embed.remote.errors import RemoteEmbedderCapabilityError


@functools.cache
def composed_class(bases: tuple[type[Embedder], ...], name: str) -> type[Embedder]:
    """Build the class that implements exactly the capabilities of one server.

    Every base carries its own concrete methods, so the result has nothing abstract left.
    The classes are cached, because a new one for every call would stay for the life of
    the process.

    Args:
        bases: The classes to compose, in a fixed order, so two servers that advertise the
            same set compose the same class.
        name: The name of the built class, for a repr and a traceback.

    Returns:
        A class that ``isinstance`` reports as each of ``bases``.
    """
    return type(name, bases, {})


def check_routable(
    advertised: Sequence[Capability],
    routable: Sequence[Capability],
    routes_to: Sequence[Capability],
    resolvable: Sequence[Capability],
) -> None:
    """Refuse a server that LightlyStudio can never ask for an embedding.

    Both errors arrive at construction, where the message can still name the real problem.
    Later, inside ``EmbedderRegistry.register``, the second one reads "implements no
    capability", which names the symptom instead.

    Args:
        advertised: The capabilities that ``/v1/describe`` reported.
        routable: The advertised capabilities that the client routes to.
        routes_to: Every capability that the client routes to.
        resolvable: The routed capabilities that ``EmbedderRegistry`` can hand back.

    Raises:
        RemoteEmbedderCapabilityError: If nothing advertised is routable, or if the only
            routable capabilities are ones that the registry cannot resolve.
    """
    if not routable:
        raise RemoteEmbedderCapabilityError(
            f"The embedding server advertises {names(capabilities=advertised)}. This client "
            f"routes to {names(capabilities=routes_to)}."
        )
    if not set(routable) & set(resolvable):
        raise RemoteEmbedderCapabilityError(
            f"The embedding server advertises {names(capabilities=advertised)}, of which "
            f"this client routes to {names(capabilities=routable)}. EmbedderRegistry "
            f"resolves {names(capabilities=resolvable)}, so nothing in LightlyStudio would "
            f"ask this embedder for a vector."
        )


def names(capabilities: Sequence[Capability]) -> str:
    """Name capabilities the way the wire writes them, for a message.

    A capability is named once: ``DescribeResponse`` validates no uniqueness.
    """
    return ", ".join(dict.fromkeys(capability.value for capability in capabilities))
