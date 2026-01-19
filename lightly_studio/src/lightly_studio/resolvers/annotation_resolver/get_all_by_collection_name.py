"""Module for retrieving annotations by collection name."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.collection_resolver import get_by_name

from .get_all import GetAllAnnotationsResult, get_all


def get_all_by_collection_name(
    session: Session,
    collection_name: str,
    pagination: Paginated | None = None,
) -> GetAllAnnotationsResult:
    """Get all annotations from a annotation collection, given by its name.

    Args:
        session: Database session.
        collection_name: Annotation collection name to query for.
        pagination: Optional pagination parameters.

    Returns:
        The paginated annotations result.

    Raises:
        ValueError: If the annotation collection with the given name does not exist.
    """
    collection = get_by_name(session=session, name=collection_name)
    if collection is None:
        raise ValueError(f"Collection with name '{collection_name}' does not exist.")

    filters = AnnotationsFilter(collection_ids=[collection.collection_id])
    return get_all(session=session, pagination=pagination, filters=filters)
