"""Implementation of add_many for annotation_collection_coverage_resolver."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation_collection_coverage import (
    AnnotationCollectionCoverageTable,
)


def add_many(
    session: Session,
    annotation_collection_id: UUID,
    parent_sample_ids: Iterable[UUID],
) -> None:
    """Insert coverage rows for the given (collection, parent_sample) pairs.

    Idempotent: pairs that already exist are skipped, so callers may safely
    re-invoke this on every annotation save without conflict errors.

    Args:
        session: SQLAlchemy session for database operations.
        annotation_collection_id: UUID of the annotation collection.
        parent_sample_ids: Parent sample IDs covered by this collection. May
            contain duplicates and may be empty.
    """
    requested_ids = set(parent_sample_ids)
    if not requested_ids:
        return

    existing_ids = set(
        session.exec(
            select(col(AnnotationCollectionCoverageTable.parent_sample_id)).where(
                col(AnnotationCollectionCoverageTable.annotation_collection_id)
                == annotation_collection_id,
                col(AnnotationCollectionCoverageTable.parent_sample_id).in_(requested_ids),
            )
        ).all()
    )

    new_rows = [
        AnnotationCollectionCoverageTable(
            annotation_collection_id=annotation_collection_id,
            parent_sample_id=parent_sample_id,
        )
        for parent_sample_id in requested_ids - existing_ids
    ]
    if not new_rows:
        return

    session.bulk_save_objects(new_rows)
    session.flush()
