"""Count how many annotations matching a filter have an embedding."""

from __future__ import annotations

from typing import NamedTuple
from uuid import UUID

from sqlmodel import Session, func, select

from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter


class EmbeddingCoverage(NamedTuple):
    """The number of annotations with an embedding, of all annotations matching a filter."""

    embedded_count: int
    total_count: int


def count_embedding_coverage(
    session: Session,
    collection_id: UUID,
    filters: AnnotationsFilter | None = None,
) -> EmbeddingCoverage:
    """Count the annotations of a collection that match a filter, and those with an embedding.

    The ``has_embedding`` and the embedding-plot region fields of the filter are ignored, so
    the counts describe the plot of the filter.

    Args:
        session: The database session.
        collection_id: The annotation collection to count in.
        filters: The annotation filters to apply.

    Returns:
        The number of matching annotations with an embedding, and of all matching annotations.
    """
    base = (filters or AnnotationsFilter()).model_copy(
        update={"has_embedding": None, "embedding_region": None, "region_sample_ids": None}
    )
    embedded = base.model_copy(update={"has_embedding": True})
    return EmbeddingCoverage(
        embedded_count=_count(session=session, collection_id=collection_id, filters=embedded),
        total_count=_count(session=session, collection_id=collection_id, filters=base),
    )


def _count(session: Session, collection_id: UUID, filters: AnnotationsFilter) -> int:
    sample_ids = filters.build_sample_ids_query(collection_id=collection_id).subquery()
    return session.exec(select(func.count()).select_from(sample_ids)).one()
