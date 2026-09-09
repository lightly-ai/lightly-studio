"""The errors an embedder can raise or provoke, in one place."""

from __future__ import annotations


class EmbedderContractError(RuntimeError):
    """Raised when an embedder returns a result the protocol does not allow.

    The server answers 500 and names the problem, rather than shipping the result to
    LightlyStudio.
    """


class CapabilityNotImplementedError(NotImplementedError):
    """Raise it from a capability method that is mounted but not finished yet.

    The server answers 501, which tells a client to re-read ``/v1/describe`` instead
    of retrying. Any other error is a failure of the model, not a retracted
    capability, and answers 500.
    """
