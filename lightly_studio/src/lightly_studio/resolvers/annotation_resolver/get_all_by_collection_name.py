"""Module for retrieving annotations by collection name."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter

from .get_all import GetAllAnnotationsResult, get_all


def get_all_by_collection_name(
    session: Session,
    collection_name: str,
    pagination: Paginated | None = None,
    filters: AnnotationsFilter | None = None,
) -> GetAllAnnotationsResult:
    """Get all annotations from a annotation collection, given by its name.

    Args:
        session: Database session.
        collection_name: Annotation collection name to query for.
        pagination: Optional pagination parameters.
        filters: Optional filters. It can not have `collection_ids` set.

    Returns:
        The paginated annotations result.
    """
    if filters is None:
        filters = AnnotationsFilter()

    if filters.collection_ids is not None:
        raise ValueError(
            "AnnotationsFilter.collection_ids should not be set when calling "
            "get_all_by_collection_name()."
        )

    filters.collection_names = [collection_name]
    return get_all(session=session, pagination=pagination, filters=filters)
