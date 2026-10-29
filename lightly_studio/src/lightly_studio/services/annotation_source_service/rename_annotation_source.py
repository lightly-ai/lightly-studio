"""Rename an annotation source."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.errors import AnnotationSourceInUseError
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import annotation_collection_coverage_resolver, collection_resolver
from lightly_studio.services import annotation_source_service
from lightly_studio.services.annotation_source_service import get_annotation_source


def rename_annotation_source(
    session: Session, dataset_collection_id: UUID, annotation_source_id: UUID, name: str
) -> UUID:
    """Rename an annotation source.

    DuckDB rejects an update of the name while other rows reference the collection. So the
    rename creates a source with the new name, moves the annotations and the coverage there
    and deletes the old source. The annotations keep their IDs, the source gets a new ID.

    Args:
        session: Database session.
        dataset_collection_id: ID of the collection that owns the annotation source.
        annotation_source_id: ID of the annotation source to rename.
        name: The new name.

    Returns:
        The ID of the renamed annotation source.

    Raises:
        NotFoundError: If the collection has no annotation source with this ID.
        ValueError: If the collection has another child with this name.
        AnnotationSourceInUseError: If evaluation runs use the annotation source.
    """
    source = get_annotation_source.get_annotation_source(
        session=session,
        dataset_collection_id=dataset_collection_id,
        annotation_source_id=annotation_source_id,
    )
    if name == source.name:
        return annotation_source_id
    _check_can_rename(session=session, source_name=source.name, source_id=annotation_source_id)
    if collection_resolver.get_by_name(
        session=session, name=name, parent_collection_id=dataset_collection_id
    ):
        raise ValueError(f"An annotation source named '{name}' already exists.")

    covered_sample_ids = annotation_collection_coverage_resolver.list_by_collection_id(
        session=session, annotation_collection_id=annotation_source_id
    )
    annotation_ids = session.exec(
        select(SampleTable.sample_id).where(col(SampleTable.collection_id) == annotation_source_id)
    ).all()
    target_id, _ = annotation_source_service.move_annotations(
        session=session,
        dataset_collection_id=dataset_collection_id,
        annotation_ids=annotation_ids,
        target_annotation_source_name=name,
    )
    annotation_collection_coverage_resolver.add_many(
        session=session, annotation_collection_id=target_id, parent_sample_ids=covered_sample_ids
    )
    session.commit()
    annotation_source_service.delete_annotation_source(
        session=session,
        dataset_collection_id=dataset_collection_id,
        annotation_source_id=annotation_source_id,
    )
    return target_id


def _check_can_rename(session: Session, source_name: str, source_id: UUID) -> None:
    evaluation_run_names = get_annotation_source.get_evaluation_run_names(
        session=session, annotation_source_id=source_id
    )
    if evaluation_run_names:
        raise AnnotationSourceInUseError(
            f"The annotation source '{source_name}' is used by the evaluation runs "
            f"{', '.join(evaluation_run_names)}. Delete these evaluation runs first."
        )
