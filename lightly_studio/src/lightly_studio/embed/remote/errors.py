"""The errors that a call to a remote embedding server can raise.

Every error of this package is a ``RemoteEmbedderError``, so a caller with no recovery for
a particular cause catches the base class alone. The subclasses name the causes that a
caller can act on, and each one says whether another attempt can change the answer.
"""

from __future__ import annotations


class RemoteEmbedderError(RuntimeError):
    """A remote embedding server did not give embeddings."""


class RemoteEmbedderUnreachableError(RemoteEmbedderError):
    """The server gave no answer.

    The connection failed, the answer did not arrive in time, or the server asked the
    client to wait for longer than the client waits. The server can answer later, so a
    caller can try again.
    """


class RemoteEmbedderAuthError(RemoteEmbedderError):
    """The server rejected the token, or it wants one and the client sent none.

    Another attempt sends the same token, so it gets the same answer. The configuration
    needs a different token.
    """


class RemoteEmbedderCapabilityError(RemoteEmbedderError):
    """The server does not serve an input kind that LightlyStudio can use.

    Raised when a server advertises no capability that this client routes to, and when a
    server answers 501 for a route that its own ``/v1/describe`` advertised.
    """


class RemoteEmbedderBatchTooLargeError(RemoteEmbedderError):
    """The server refused the request as too large.

    The client already splits a batch to the ``max_batch_size`` that ``/v1/describe``
    reports, so this names a single item that is too large on its own, or a batch of items
    that together pass ``max_request_bytes``. Sending the same items again does not help.
    """


class RemoteEmbedderProtocolError(RemoteEmbedderError):
    """The exchange broke the contract of the protocol.

    The server answered a status that it cannot answer here, a body that does not parse,
    or vectors that disagree with what ``/v1/describe`` reported. Another attempt sends the
    same request to the same server, so it gets the same answer.
    """
