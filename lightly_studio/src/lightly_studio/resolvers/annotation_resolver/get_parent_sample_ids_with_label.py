"""Find parent samples that already carry a given annotation label."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.database import db_array
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.sample import SampleTable


def get_parent_sample_ids_with_label(
    session: Session,
    parent_sample_ids: Sequence[UUID],
    annotation_label_id: UUID,
    annotation_collection_id: UUID,
) -> set[UUID]:
    """Return the parent samples that already have an annotation with the given label.

    The collection filter is applied on the annotation's own sample
    (``AnnotationBaseTable.sample_id -> SampleTable.collection_id``), not on the
    parent sample's collection.

    Args:
        session: Database session.
        parent_sample_ids: Parent sample IDs to check.
        annotation_label_id: ID of the annotation label to look for.
        annotation_collection_id: ID of the collection the annotation samples must belong to.

    Returns:
        The subset of ``parent_sample_ids`` that already have such an annotation.
    """
    if not parent_sample_ids:
        return set()

    statement = (
        select(AnnotationBaseTable.parent_sample_id)
        .join(
            SampleTable,
            col(SampleTable.sample_id) == col(AnnotationBaseTable.sample_id),
        )
        .where(col(SampleTable.collection_id) == annotation_collection_id)
        .where(col(AnnotationBaseTable.annotation_label_id) == annotation_label_id)
        .where(
            db_array.in_array(
                column=col(AnnotationBaseTable.parent_sample_id),
                values=list(parent_sample_ids),
            )
        )
        .distinct()
    )
    return set(session.exec(statement).all())
