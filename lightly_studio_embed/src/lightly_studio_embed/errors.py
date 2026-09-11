"""The errors that an embedder can raise or cause, in one module."""

from __future__ import annotations


class EmbedderContractError(RuntimeError):
    """The embedder returned a result that the protocol does not allow.

    The server answers 500 and names the problem. It does not send the result to
    LightlyStudio.
    """
