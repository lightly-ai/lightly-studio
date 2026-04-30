"""Implementation of list_by_collection_id for annotation_collection_coverage_resolver."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation_collection_coverage import (
    AnnotationCollectionCoverageTable,
)


def list_by_collection_id(session: Session, annotation_collection_id: UUID) -> list[UUID]:
    """Return parent sample IDs covered by the given annotation collection."""
    return list(
        session.exec(
            select(col(AnnotationCollectionCoverageTable.parent_sample_id)).where(
                col(AnnotationCollectionCoverageTable.annotation_collection_id)
                == annotation_collection_id
            )
        ).all()
    )
