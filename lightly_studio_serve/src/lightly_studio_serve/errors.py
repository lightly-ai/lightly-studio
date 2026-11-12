"""The errors that an embedder can raise or cause, in one module."""

from __future__ import annotations


class EmbedderContractError(RuntimeError):
    """The embedder returned a result that the protocol does not allow.

    The server answers 500 and names the problem. It does not send the result to
    LightlyStudio.
    """


class LabelingModelError(RuntimeError):
    """The labeling model failed, or returned a prediction that the protocol does not allow.

    The server answers 500 and names the problem. It does not send the predictions to
    LightlyStudio.
    """
