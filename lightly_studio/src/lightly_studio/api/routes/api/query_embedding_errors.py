"""Maps the errors of resolving a query embedder to HTTP errors."""

from __future__ import annotations

from typing import Union

from fastapi import HTTPException

from lightly_studio.api.routes.api.status import HTTP_STATUS_BAD_GATEWAY, HTTP_STATUS_CONFLICT
from lightly_studio.embed.errors import (
    MissingCapabilityError,
    NoDefaultEmbeddingModelError,
    RemoteEmbedderUnavailableError,
)

QueryEmbedderError = Union[
    NoDefaultEmbeddingModelError, MissingCapabilityError, RemoteEmbedderUnavailableError
]
QUERY_EMBEDDER_ERRORS = (
    NoDefaultEmbeddingModelError,
    MissingCapabilityError,
    RemoteEmbedderUnavailableError,
)


def to_http_exception(exc: QueryEmbedderError, input_kind: str) -> HTTPException:
    """Get the HTTP error for a query the collection cannot answer.

    A space without the capability and a collection without a default model are conflicts
    the user can fix. An embedding server that cannot be used is a bad gateway.

    Args:
        exc: The error of resolving the query embedder.
        input_kind: What the query embeds, such as "text" or "images".

    Returns:
        The HTTP error to raise.
    """
    if isinstance(exc, RemoteEmbedderUnavailableError):
        return HTTPException(status_code=HTTP_STATUS_BAD_GATEWAY, detail=f"{exc}")
    if isinstance(exc, MissingCapabilityError):
        return HTTPException(
            status_code=HTTP_STATUS_CONFLICT,
            detail=(
                f"The embedding space {exc.space_key!r} of this collection cannot embed "
                f"{input_kind}."
            ),
        )
    return HTTPException(status_code=HTTP_STATUS_CONFLICT, detail=f"{exc}")
