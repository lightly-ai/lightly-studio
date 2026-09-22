"""The errors that a call to a remote embedding server can raise.

Every error of this package is a ``RemoteEmbedderError``, so a caller with no recovery for
a particular cause catches the base class alone. The subclasses name the causes that a
caller can act on. Only ``RemoteEmbedderUnreachableError`` can give a different answer on
another attempt: every other cause repeats itself until the server or the configuration
changes.
"""

from __future__ import annotations


class RemoteEmbedderError(RuntimeError):
    """A remote embedding server did not give embeddings."""


class RemoteEmbedderUnreachableError(RemoteEmbedderError):
    """The server gave no answer.

    The connection failed, the answer did not arrive in time, or the server asked the
    client to wait for longer than the client waits.
    """


class RemoteEmbedderAuthError(RemoteEmbedderError):
    """The server rejected the token, or it wants one and the client sent none."""


class RemoteEmbedderConfigError(RemoteEmbedderError):
    """The stored configuration cannot name a usable server.

    The URL does not parse, or the server produces another embedding space than the
    configuration names. Vectors of another space are meaningless next to the stored ones.
    """


class RemoteEmbedderCapabilityError(RemoteEmbedderError):
    """The server does not serve an input kind that LightlyStudio can use.

    Raised when a server advertises no capability that this client routes to, when the
    capabilities it does route to are ones that ``EmbedderRegistry`` cannot resolve, and
    when a server answers 501 for a route that its own ``/v1/describe`` advertised.
    """


class RemoteEmbedderBatchTooLargeError(RemoteEmbedderError):
    """The server refused the request as too large.

    The client already splits a batch to the ``max_batch_size`` that ``/v1/describe``
    reports, so this names a single item that is too large on its own, or a batch of items
    that together pass ``max_request_bytes``.
    """


class RemoteEmbedderProtocolError(RemoteEmbedderError):
    """The exchange broke the contract of the protocol.

    The server answered a status that it cannot answer here, a body that does not parse,
    or vectors that disagree with what ``/v1/describe`` reported.
    """
