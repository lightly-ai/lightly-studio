"""Delete an annotation source with all its annotations."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.errors import AnnotationSourceInUseError
from lightly_studio.export import export_artifact
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    evaluation_run_resolver,
    sample_resolver,
)
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
        AnnotationSourceInUseError: If evaluation runs use the annotation source or it has
            child collections.
    """
    source = get_annotation_source.get_annotation_source(
        session=session,
        dataset_collection_id=dataset_collection_id,
        annotation_source_id=annotation_source_id,
    )
    _check_not_in_use(session=session, source=source)
    return _delete_source(session=session, source=source)


def _check_not_in_use(session: Session, source: CollectionTable) -> None:
    """Check that the annotation source can be deleted.

    Raises:
        AnnotationSourceInUseError: If evaluation runs use the annotation source or if it has
            child collections other than captions, or captions with captions.
    """
    evaluation_run_names = evaluation_run_resolver.get_names_by_collection_id(
        session=session, collection_id=source.collection_id
    )
    if evaluation_run_names:
        raise AnnotationSourceInUseError(
            f"The annotation source '{source.name}' is used by the evaluation runs "
            f"{', '.join(evaluation_run_names)}. Delete these evaluation runs first."
        )
    # The delete removes the captions of the annotations, but no other attached data and no
    # captions of these captions.
    child_names = sorted(
        child.name
        for child in source.children
        if child.sample_type != SampleType.CAPTION or child.children
    )
    if child_names:
        raise AnnotationSourceInUseError(
            f"The annotation source '{source.name}' cannot be deleted because "
            f"it has data attached: {', '.join(child_names)}."
        )


def _delete_source(session: Session, source: CollectionTable) -> int:
    """Delete an annotation source with its annotations and the rows that point at it.

    Also deletes the captions of the annotations and their child collections. The caller
    checks that the annotation source is not in use, so all child collections are caption
    collections. The delete commits several times and is not atomic, see
    ``annotation_resolver.delete_annotations_by_ids``.

    Returns:
        The number of deleted annotations.
    """
    # TODO(Gabriel, 11/2026): Run the delete in one transaction on PostgreSQL, like
    # delete_dataset.py. A caption, evaluation run or annotation that is created after the
    # check can make the delete fail after earlier steps are committed. DuckDB needs the
    # commits, so make each step safe to run again there.
    source_id = source.collection_id
    child_ids = [child.collection_id for child in source.children]
    annotation_ids = annotation_resolver.get_sample_ids(session=session, collection_id=source_id)
    deleted_count = annotation_resolver.delete_annotations_by_ids(
        session=session, annotation_ids=list(annotation_ids)
    )
    # Delete the children first, they reference the annotation source.
    for child_id in child_ids:
        sample_resolver.delete_caption_samples(session=session, collection_id=child_id)
    for collection_id in [*child_ids, source_id]:
        export_paths = collection_resolver.delete_dependent_rows(
            session=session, collection_id=collection_id
        )
        # DuckDB rejects the delete of the collection in the transaction that deleted its
        # referencing rows, so commit first.
        session.commit()
        collection_resolver.delete(session=session, collection_id=collection_id)
        # Remove the files only after the commit, so that a rollback keeps no job without a file.
        for export_path in export_paths:
            export_artifact.remove_export_artifact(export_path=export_path)
    return deleted_count
