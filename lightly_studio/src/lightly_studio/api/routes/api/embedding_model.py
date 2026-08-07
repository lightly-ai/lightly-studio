"""This module contains the API routes for embedding models and their serving endpoints.

A collection's embedding model may live outside this process: customers who index with
their own model run it behind an HTTP service on their own network, and the browser calls
that service directly for search queries. These routes expose which model a collection was
embedded with and where it is served from.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel

from lightly_studio.api.routes.api import collection
from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_NOT_FOUND,
)
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.models.collection import CollectionTable
from lightly_studio.resolvers import embedding_model_resolver, embedding_model_service_resolver

embedding_model_router = APIRouter()


class EmbeddingModelView(BaseModel):
    """The model a collection's stored embeddings were produced with.

    Attributes:
        embedding_model_hash: A customer-declared identifier, not a digest of the
            weights. The rule is to bump it whenever the output vectors change.
        serving_url: Where a live copy of the model is served for search queries, or
            None when the model runs inside this process. The browser calls it directly,
            so this host must be reachable from the user's machine.
    """

    embedding_model_id: UUID
    name: str
    embedding_model_hash: str
    embedding_dimension: int
    serving_url: str | None


class UpdateServingUrlRequest(BaseModel):
    """Request body for pointing a model at an embedding service.

    Attributes:
        serving_url: Base URL of the service, or None to stop serving the model.
    """

    serving_url: str | None


@embedding_model_router.get("/collections/{collection_id}/embedding_model")
def read_embedding_model(
    session: SessionDep,
    collection_row: Annotated[
        CollectionTable,
        Path(title="Collection Id"),
        Depends(collection.get_and_validate_collection_id),
    ],
) -> EmbeddingModelView | None:
    """Return the collection's embedding model, or None if it has none."""
    embedding_model = embedding_model_resolver.get_default_by_collection_id(
        session=session, collection_id=collection_row.collection_id
    )
    if embedding_model is None:
        return None

    service = embedding_model_service_resolver.get_by_model_hash(
        session=session, embedding_model_hash=embedding_model.embedding_model_hash
    )
    return EmbeddingModelView(
        embedding_model_id=embedding_model.embedding_model_id,
        name=embedding_model.name,
        embedding_model_hash=embedding_model.embedding_model_hash,
        embedding_dimension=embedding_model.embedding_dimension,
        serving_url=service.serving_url if service is not None else None,
    )


@embedding_model_router.put("/embedding_models/{embedding_model_hash}/serving_url")
def update_embedding_model_serving_url(
    session: SessionDep,
    embedding_model_hash: Annotated[str, Path(title="Embedding model hash")],
    request: UpdateServingUrlRequest,
) -> UpdateServingUrlRequest:
    """Point a model at an embedding service, or clear its URL.

    Keyed on the model hash rather than a collection, so one update covers every
    collection embedded with that model.

    TODO(Jonas, 08/2026): Restrict this to admins. Whoever sets a serving URL redirects
    every user's queries and uploaded images to a host of their choosing, and the request
    never touches our servers, so there is no trace of it here. Authentication is
    terminated by a proxy outside this repository, so the check cannot be written yet.
    """
    if not embedding_model_resolver.exists_by_model_hash(
        session=session, embedding_model_hash=embedding_model_hash
    ):
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=(
                f"No collection was embedded with model '{embedding_model_hash}'. Index with "
                f"the model before pointing Lightly Studio at a service for it."
            ),
        )

    if request.serving_url is None:
        embedding_model_service_resolver.delete_by_model_hash(
            session=session, embedding_model_hash=embedding_model_hash
        )
        return UpdateServingUrlRequest(serving_url=None)

    try:
        service = embedding_model_service_resolver.set_serving_url(
            session=session,
            embedding_model_hash=embedding_model_hash,
            serving_url=request.serving_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=HTTP_STATUS_BAD_REQUEST, detail=f"{exc}") from None

    return UpdateServingUrlRequest(serving_url=service.serving_url)
