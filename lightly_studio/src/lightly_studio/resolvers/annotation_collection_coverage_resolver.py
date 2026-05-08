"""Resolver for annotation collection coverage."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, select

from lightly_studio.models.annotation_collection_coverage import (
    AnnotationCollectionCoverageTable,
)


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

    # Use database-level conflict handling (idempotent across both Postgres and DuckDB).
    dialect_name = session.get_bind().dialect.name if session.get_bind() else None
    if dialect_name == "postgresql":
        session.exec(
            pg_insert(AnnotationCollectionCoverageTable).values(rows).on_conflict_do_nothing()
        )
    else:
        # DuckDB and SQLite: use OR IGNORE prefix.
        session.exec(
            insert(AnnotationCollectionCoverageTable).values(rows).prefix_with("OR IGNORE")
        )
    session.flush()


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
