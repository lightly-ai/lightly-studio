"""Get an annotation source of a collection."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, or_, select

from lightly_studio.errors import NotFoundError
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.evaluation_run import EvaluationRunTable
from lightly_studio.resolvers import collection_resolver


def get_annotation_source(
    session: Session, dataset_collection_id: UUID, annotation_source_id: UUID
) -> CollectionTable:
    """Return the annotation source collection that is a child of the given collection.

    Raises:
        NotFoundError: If the collection has no annotation source with this ID.
    """
    source = collection_resolver.get_by_id(session=session, collection_id=annotation_source_id)
    if (
        source is None
        or source.sample_type != SampleType.ANNOTATION
        or source.parent_collection_id != dataset_collection_id
    ):
        raise NotFoundError(f"Annotation source {annotation_source_id} not found.")
    return source


def get_evaluation_run_names(session: Session, annotation_source_id: UUID) -> list[str]:
    """Return the names of the evaluation runs that use the annotation source."""
    return list(
        session.exec(
            select(EvaluationRunTable.name)
            .where(
                or_(
                    col(EvaluationRunTable.gt_annotation_collection_id) == annotation_source_id,
                    col(EvaluationRunTable.pred_annotation_collection_id) == annotation_source_id,
                )
            )
            .order_by(col(EvaluationRunTable.name))
        ).all()
    )
