"""Implementation of count_by_collection_id for annotation_collection_coverage_resolver."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, func, select

from lightly_studio.models.annotation_collection_coverage import (
    AnnotationCollectionCoverageTable,
)


def count_by_collection_id(session: Session, annotation_collection_id: UUID) -> int:
    """Count the number of parent samples covered by the given annotation collection."""
    return session.exec(
        select(func.count())
        .select_from(AnnotationCollectionCoverageTable)
        .where(
            col(AnnotationCollectionCoverageTable.annotation_collection_id)
            == annotation_collection_id
        )
    ).one()
