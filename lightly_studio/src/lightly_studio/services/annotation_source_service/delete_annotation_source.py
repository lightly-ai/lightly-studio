"""Delete an annotation source with all its annotations."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, delete, or_, select

from lightly_studio.errors import AnnotationSourceInUseError
from lightly_studio.models.annotation_collection_coverage import (
    AnnotationCollectionCoverageTable,
)
from lightly_studio.models.collection_embedding_model import CollectionEmbeddingModelTable
from lightly_studio.models.embedding_plot import EmbeddingPlotTable
from lightly_studio.models.evaluation_run import EvaluationRunTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.tag import TagTable
from lightly_studio.resolvers import annotation_resolver, collection_resolver
from lightly_studio.services.annotation_source_service import get_annotation_source


def delete_annotation_source(
    session: Session, dataset_collection_id: UUID, annotation_source_id: UUID
) -> int:
    """Delete an annotation source, its annotations and the rows that point at it.

    The delete is not atomic, see ``annotation_resolver.delete_annotations_by_ids``.

    Args:
        session: Database session.
        dataset_collection_id: ID of the collection that owns the annotation source.
        annotation_source_id: ID of the annotation source collection.

    Returns:
        The number of deleted annotations.

    Raises:
        NotFoundError: If the collection has no annotation source with this ID.
        AnnotationSourceInUseError: If evaluation runs use the annotation source.
    """
    source = get_annotation_source.get_annotation_source(
        session=session,
        dataset_collection_id=dataset_collection_id,
        annotation_source_id=annotation_source_id,
    )
    evaluation_run_names = _get_evaluation_run_names(
        session=session, annotation_source_id=annotation_source_id
    )
    if evaluation_run_names:
        raise AnnotationSourceInUseError(
            f"The annotation source '{source.name}' is used by the evaluation runs "
            f"{', '.join(evaluation_run_names)}. Delete these evaluation runs first."
        )

    # An annotation ID is the sample ID of its row in the annotation source collection.
    annotation_ids = list(
        session.exec(
            select(SampleTable.sample_id).where(
                col(SampleTable.collection_id) == annotation_source_id
            )
        ).all()
    )
    deleted_count = annotation_resolver.delete_annotations_by_ids(
        session=session, annotation_ids=annotation_ids
    )
    # DuckDB rejects the delete of the collection in the transaction that deleted its
    # referencing rows, so commit first.
    for table, column in (
        (
            AnnotationCollectionCoverageTable,
            AnnotationCollectionCoverageTable.annotation_collection_id,
        ),
        (CollectionEmbeddingModelTable, CollectionEmbeddingModelTable.collection_id),
        (EmbeddingPlotTable, EmbeddingPlotTable.collection_id),
        (TagTable, TagTable.collection_id),
    ):
        session.exec(delete(table).where(col(column) == annotation_source_id))
    session.commit()
    collection_resolver.delete(session=session, collection_id=annotation_source_id)
    return deleted_count


def _get_evaluation_run_names(session: Session, annotation_source_id: UUID) -> list[str]:
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
