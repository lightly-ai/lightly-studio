"""Resolve the number of annotations in annotation collections."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.orm import aliased
from sqlmodel import Session, col, func, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.sample import SampleTable


def get_annotation_counts_by_collection_ids(
    session: Session,
    collection_ids: Sequence[UUID],
) -> dict[UUID, int]:
    """Return the number of annotations in each annotation collection.

    Args:
        session: The database session.
        collection_ids: Annotation collection IDs to count.

    Returns:
        Mapping of collection ID to its annotation count. Collections without
        annotations are omitted.
    """
    if not collection_ids:
        return {}

    sample = aliased(SampleTable)
    statement = (
        select(col(sample.collection_id), func.count())
        .select_from(AnnotationBaseTable)
        .join(sample, AnnotationBaseTable.sample)
        .where(col(sample.collection_id).in_(collection_ids))
        .group_by(col(sample.collection_id))
    )
    return dict(session.exec(statement).all())
