"""Resolver for annotation collection coverage."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.database import db_insert
from lightly_studio.models.annotation_collection_coverage import (
    AnnotationCollectionCoverageTable,
)
from lightly_studio.models.sequence import SampleSequenceLinkTable


def add_many(
    session: Session,
    annotation_collection_id: UUID,
    parent_sample_ids: Iterable[UUID],
) -> None:
    """Insert coverage rows for the given (collection, parent_sample) pairs.

    Idempotent: pairs that already exist are skipped via database-level conflict
    handling, so callers may safely re-invoke this on every annotation save
    without race conditions.

    Args:
        session: SQLAlchemy session for database operations.
        annotation_collection_id: UUID of the annotation collection.
        parent_sample_ids: Parent sample IDs covered by this collection. May
            contain duplicates and may be empty.
    """
    ids = set(parent_sample_ids)
    if not ids:
        return

    rows = [
        {
            "annotation_collection_id": annotation_collection_id,
            "parent_sample_id": sample_id,
        }
        for sample_id in ids
    ]
    db_insert.insert_ignoring_conflicts(
        session=session, table=AnnotationCollectionCoverageTable, rows=rows
    )
    session.flush()


def sequence_sample_ids(session: Session, annotation_collection_id: UUID) -> set[UUID]:
    """Return sequences that already have groups covered by this annotation source."""
    rows = session.exec(
        select(SampleSequenceLinkTable.sequence_sample_id)
        .join(
            AnnotationCollectionCoverageTable,
            col(AnnotationCollectionCoverageTable.parent_sample_id)
            == col(SampleSequenceLinkTable.sample_id),
        )
        .where(
            col(AnnotationCollectionCoverageTable.annotation_collection_id)
            == annotation_collection_id
        )
        .distinct()
    ).all()
    return set(rows)


def list_by_collection_id(session: Session, annotation_collection_id: UUID) -> list[UUID]:
    """Return parent sample IDs covered by the given annotation collection.

    Args:
        session: SQLAlchemy session for database operations.
        annotation_collection_id: UUID of the annotation collection.

    Returns:
        List of parent sample IDs that this collection was applied to.
    """
    return list(
        session.exec(
            select(AnnotationCollectionCoverageTable.parent_sample_id).where(
                AnnotationCollectionCoverageTable.annotation_collection_id
                == annotation_collection_id
            )
        ).all()
    )
