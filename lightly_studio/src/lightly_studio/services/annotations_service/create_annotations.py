"""Create annotations in bulk."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationCreate
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    annotation_collection_coverage_resolver,
    annotation_resolver,
    collection_resolver,
    evaluation_run_resolver,
)


def create_annotations(
    session: Session,
    parent_collection_id: UUID,
    annotations: Sequence[AnnotationCreate],
    collection_name: str | None,
    covered_sample_ids: Sequence[UUID],
) -> list[UUID]:
    """Create annotations and mark the evaluation runs of their annotation collection stale.

    The evaluation runs become stale only if the function creates annotations.

    Args:
        session: Database session for executing the operation.
        parent_collection_id: The ID of the collection of the annotated samples.
        annotations: The annotations to create.
        collection_name: The name of the annotation collection. None uses the default.
        covered_sample_ids: Parent samples that the annotation collection covers, also
            samples without annotations.

    Returns:
        The IDs of the new annotations, in the order of `annotations`.
    """
    annotation_ids = annotation_resolver.create_many(
        session=session,
        parent_collection_id=parent_collection_id,
        annotations=list(annotations),
        collection_name=collection_name,
    )
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=session,
        collection_id=parent_collection_id,
        sample_type=SampleType.ANNOTATION,
        name=collection_name,
    )
    annotation_collection_coverage_resolver.add_many(
        session=session,
        annotation_collection_id=annotation_collection_id,
        parent_sample_ids=covered_sample_ids,
    )
    session.commit()
    if annotation_ids:
        evaluation_run_resolver.mark_stale_by_collection_id(
            session=session, collection_id=annotation_collection_id
        )
    return annotation_ids
