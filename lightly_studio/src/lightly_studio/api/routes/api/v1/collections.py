"""v1 routes to read collections."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from sqlmodel import Session

from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import NotFoundError
from lightly_studio.models.collection import CollectionTable, CollectionWithoutChildrenView
from lightly_studio.resolvers import collection_resolver

collections_router = APIRouter()


@collections_router.get("/collections", response_model=list[CollectionWithoutChildrenView])
def v1_read_collections(
    session: SessionDep, parent_collection_id: UUID | None = None, name: str | None = None
) -> list[CollectionTable]:
    """Get the child collections of a parent. Without a parent, get the root collections."""
    return collection_resolver.get_all_by_parent(
        session=session, parent_collection_id=parent_collection_id, name=name
    )


@collections_router.get(
    "/collections/{collection_id}", response_model=CollectionWithoutChildrenView
)
def v1_read_collection(session: SessionDep, collection_id: UUID) -> CollectionTable:
    """Get a collection by ID."""
    return get_collection(session=session, collection_id=collection_id)


def get_collection(session: Session, collection_id: UUID) -> CollectionTable:
    """Get a collection by ID.

    Raises:
        NotFoundError: If the collection does not exist.
    """
    collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
    if collection is None:
        raise NotFoundError(f"Collection with ID {collection_id} not found.")
    return collection
