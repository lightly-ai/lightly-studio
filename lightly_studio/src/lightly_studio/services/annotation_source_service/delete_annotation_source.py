"""Delete an annotation source with all its annotations."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.errors import AnnotationSourceInUseError, NotFoundError
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.resolvers import (
    collection_resolver,
    evaluation_run_resolver,
    export_job_resolver,
)


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
        AnnotationSourceInUseError: If evaluation runs or export jobs use the annotation source.
    """
    source = _get_annotation_source(
        session=session,
        dataset_collection_id=dataset_collection_id,
        annotation_source_id=annotation_source_id,
    )
    _check_not_in_use(session=session, source=source)
    return collection_resolver.delete_subtree(session=session, collection_id=source.collection_id)


def _get_annotation_source(
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


def _check_not_in_use(session: Session, source: CollectionTable) -> None:
    """Check that the annotation source can be deleted.

    Raises:
        AnnotationSourceInUseError: If evaluation runs or export jobs use the annotation source
            or one of its descendant collections.
    """
    evaluation_run_names = evaluation_run_resolver.get_names_by_collection_id(
        session=session, collection_id=source.collection_id
    )
    if evaluation_run_names:
        raise AnnotationSourceInUseError(
            f"The annotation source '{source.name}' is used by the evaluation runs "
            f"{', '.join(evaluation_run_names)}. Delete these evaluation runs first."
        )
    # TODO(Gabriel, 11/2026): Delete the export jobs and their files with the annotation source,
    # then remove this check.
    collection_ids = collection_resolver.get_subtree_ids(
        session=session, collection_id=source.collection_id
    )
    if export_job_resolver.exists_for_collection_ids(
        session=session, collection_ids=collection_ids
    ):
        raise AnnotationSourceInUseError(
            f"The annotation source '{source.name}' cannot be deleted because it was exported."
        )
