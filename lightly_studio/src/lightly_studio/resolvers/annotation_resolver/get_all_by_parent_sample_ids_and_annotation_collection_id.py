"""Get annotations for parent samples filtered to a specific annotation collection."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.orm import contains_eager
from sqlmodel import Session, col, select

from lightly_studio.database import db_array
from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationType,
)
from lightly_studio.models.sample import SampleTable


def get_all_by_parent_sample_ids_and_annotation_collection_id(
    session: Session,
    parent_sample_ids: Sequence[UUID],
    annotation_collection_id: UUID,
    annotation_types: Sequence[AnnotationType] | None = None,
) -> list[AnnotationBaseTable]:
    """Get annotations for parent samples filtered to a specific annotation collection.

    The collection filter is applied on the crop sample's collection
    (``AnnotationBaseTable.sample_id → SampleTable.collection_id``), not on
    the parent sample's collection.

    Args:
        session: Database session.
        parent_sample_ids: Parent sample IDs to fetch annotations for.
        annotation_collection_id: ID of the collection that annotation crop samples
            must belong to.
        annotation_types: Optional annotation types to filter by. ``None`` means
            no filtering. An empty sequence returns no results.

    Returns:
        Annotations belonging to the given parent samples and annotation collection.
    """
    if not parent_sample_ids:
        return []
    if annotation_types is not None and not annotation_types:
        return []
    statement = (
        select(AnnotationBaseTable)
        .join(
            SampleTable,
            col(SampleTable.sample_id) == col(AnnotationBaseTable.sample_id),
        )
        .where(
            db_array.in_array(
                column=col(AnnotationBaseTable.parent_sample_id),
                values=list(parent_sample_ids),
            )
        )
        .where(col(SampleTable.collection_id) == annotation_collection_id)
        .options(contains_eager(AnnotationBaseTable.sample).load_only(SampleTable.collection_id))  # type: ignore[arg-type]
    )
    if annotation_types is not None:
        statement = statement.where(col(AnnotationBaseTable.annotation_type).in_(annotation_types))
    return list(session.exec(statement).all())
