"""Move annotations to another annotation source."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.collection import SampleType
from lightly_studio.models.collection_embedding_model import CollectionEmbeddingModelTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import (
    annotation_collection_coverage_resolver,
    annotation_resolver,
    collection_embedding_model_resolver,
    collection_resolver,
    embedding_plot_resolver,
    evaluation_run_resolver,
)
from lightly_studio.services.annotation_source_service import get_annotation_source
from lightly_studio.utils import batching


def move_annotations(
    session: Session,
    dataset_collection_id: UUID,
    annotation_ids: Sequence[UUID],
    target_annotation_source_name: str,
) -> tuple[UUID, int]:
    """Move annotations to an annotation source, creating the source if it does not exist.

    The annotations keep their IDs, tags and embeddings. Their evaluation metrics are deleted
    and the evaluation runs of the old and the new annotation source are marked stale. The old
    annotation source keeps its coverage of the parent samples. IDs that do not exist and
    annotations that already are in the target source are ignored.

    Args:
        session: Database session.
        dataset_collection_id: ID of the collection that owns the annotation sources.
        annotation_ids: IDs of the annotations to move.
        target_annotation_source_name: Name of the annotation source to move them to.

    Returns:
        The ID of the target annotation source and the number of moved annotations.

    Raises:
        NotFoundError: If the target name or the source of an annotation is not an
            annotation source of the collection.
    """
    rows = _get_annotation_rows(session=session, annotation_ids=annotation_ids)
    for source_id in {source_id for _, source_id, _ in rows}:
        get_annotation_source.get_annotation_source(
            session=session,
            dataset_collection_id=dataset_collection_id,
            annotation_source_id=source_id,
        )
    target_id = collection_resolver.get_or_create_child_collection(
        session=session,
        collection_id=dataset_collection_id,
        sample_type=SampleType.ANNOTATION,
        name=target_annotation_source_name,
    )
    get_annotation_source.get_annotation_source(
        session=session, dataset_collection_id=dataset_collection_id, annotation_source_id=target_id
    )
    rows = [row for row in rows if row[1] != target_id]
    if not rows:
        return target_id, 0

    moved_ids = [annotation_id for annotation_id, _, _ in rows]
    source_ids = {source_id for _, source_id, _ in rows}
    for source_id in source_ids:
        _link_embedding_models(session=session, source_id=source_id, target_id=target_id)

    # Mark the plots of the old sources before the move and of the target after it.
    embedding_plot_resolver.mark_dirty(session=session, sample_ids=moved_ids)
    annotation_resolver.delete_evaluation_metrics(
        session=session,
        annotation_ids=moved_ids,
        parent_sample_ids=list({parent_id for _, _, parent_id in rows}),
    )
    session.commit()
    annotation_resolver.move_to_collection(
        session=session, annotation_ids=moved_ids, collection_id=target_id
    )
    annotation_collection_coverage_resolver.add_many(
        session=session,
        annotation_collection_id=target_id,
        parent_sample_ids=[parent_id for _, _, parent_id in rows],
    )
    embedding_plot_resolver.mark_dirty(session=session, sample_ids=moved_ids)
    session.commit()
    for collection_id in source_ids | {target_id}:
        evaluation_run_resolver.mark_stale_by_collection_id(
            session=session, collection_id=collection_id
        )
    return target_id, len(moved_ids)


def _get_annotation_rows(
    session: Session, annotation_ids: Sequence[UUID]
) -> list[tuple[UUID, UUID, UUID]]:
    """Return (annotation ID, annotation source ID, parent sample ID) of existing annotations."""
    rows: list[tuple[UUID, UUID, UUID]] = []
    for batch in batching.batched(items=set(annotation_ids)):
        rows.extend(
            session.exec(
                select(
                    AnnotationBaseTable.sample_id,
                    SampleTable.collection_id,
                    AnnotationBaseTable.parent_sample_id,
                )
                .join(SampleTable, col(SampleTable.sample_id) == col(AnnotationBaseTable.sample_id))
                .where(col(AnnotationBaseTable.sample_id).in_(batch))
            ).all()
        )
    return rows


def _link_embedding_models(session: Session, source_id: UUID, target_id: UUID) -> None:
    """Link the embedding models of the source to the target, so moved embeddings stay usable.

    The target takes over the default model of the source if it has no default yet.
    """
    links = session.exec(
        select(CollectionEmbeddingModelTable).where(
            col(CollectionEmbeddingModelTable.collection_id) == source_id
        )
    ).all()
    for link in links:
        collection_embedding_model_resolver.get_or_add_collection_model(
            session=session, collection_id=target_id, embedding_model_id=link.embedding_model_id
        )
    default_id = collection_embedding_model_resolver.get_default_by_collection_id(
        session=session, collection_id=source_id
    )
    has_target_default = collection_embedding_model_resolver.has_default_by_collection_id(
        session=session, collection_id=target_id
    )
    if default_id is not None and not has_target_default:
        collection_embedding_model_resolver.set_default(
            session=session, collection_id=target_id, embedding_model_id=default_id
        )
