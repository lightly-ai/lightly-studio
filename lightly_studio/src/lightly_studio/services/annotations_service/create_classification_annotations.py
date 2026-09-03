"""Bulk creation of classification annotations."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.models.annotation_label import AnnotationLabelCreate
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    annotation_label_resolver,
    annotation_resolver,
    collection_resolver,
    evaluation_run_resolver,
    grid_filter_region,
)
from lightly_studio.resolvers.grid_filter_base import GridFilterBase

# Number of annotations inserted per `annotation_resolver.create_many` call. Bounds the
# size of the dedupe query and of a single bulk insert for large selections.
CREATE_BATCH_SIZE = 500


class ClassificationAnnotationsCreated(BaseModel):
    """Outcome of a bulk classification annotation creation.

    Attributes:
        created_annotation_ids: IDs of the annotations that were created.
        created_count: Number of annotations that were created.
        skipped_count: Number of samples that already had the annotation class and
            were therefore left untouched.
    """

    created_annotation_ids: list[UUID]
    created_count: int
    skipped_count: int


def create_classification_annotations(
    session: Session,
    collection_id: UUID,
    class_name: str,
    sample_ids: Sequence[UUID],
    annotation_collection_name: str | None = None,
) -> ClassificationAnnotationsCreated:
    """Create a classification annotation on each of the given samples.

    The annotation class is created if the dataset does not have it yet. Existing
    annotations are never modified: samples that already have the annotation class in
    the target annotation source are skipped, other annotation classes are kept
    alongside the new one.

    Args:
        session: Database session.
        collection_id: ID of the collection the samples belong to.
        class_name: Name of the annotation class to assign.
        sample_ids: IDs of the samples to annotate. Duplicates are collapsed.
        annotation_collection_name: Name of the annotation source to create the
            annotations in. If `None`, a default name is used.

    Returns:
        The created annotation IDs together with the created and skipped counts.
    """
    return _create_classifications(
        session=session,
        collection_id=collection_id,
        class_name=class_name,
        # Collapse duplicates, otherwise a repeated id would be annotated twice.
        parent_sample_ids=list(dict.fromkeys(sample_ids)),
        annotation_collection_name=annotation_collection_name,
    )


def create_classification_annotations_by_filter(
    session: Session,
    collection_id: UUID,
    class_name: str,
    grid_filter: GridFilterBase,
    annotation_collection_name: str | None = None,
) -> ClassificationAnnotationsCreated:
    """Create a classification annotation on every sample a grid filter matches.

    The filter is resolved to sample IDs server-side and then handled exactly like
    `create_classification_annotations`.

    Args:
        session: Database session.
        collection_id: ID of the collection to match samples in.
        class_name: Name of the annotation class to assign.
        grid_filter: Filter selecting the samples to annotate.
        annotation_collection_name: Name of the annotation source to create the
            annotations in. If `None`, a default name is used.

    Returns:
        The created annotation IDs together with the created and skipped counts.
    """
    grid_filter_region.resolve_region_sample_ids(
        session=session, collection_id=collection_id, grid_filter=grid_filter
    )
    sample_ids_query = grid_filter.build_sample_ids_query(collection_id=collection_id)
    return _create_classifications(
        session=session,
        collection_id=collection_id,
        class_name=class_name,
        parent_sample_ids=list(session.exec(sample_ids_query).all()),
        annotation_collection_name=annotation_collection_name,
    )


def _create_classifications(
    session: Session,
    collection_id: UUID,
    class_name: str,
    parent_sample_ids: Sequence[UUID],
    annotation_collection_name: str | None,
) -> ClassificationAnnotationsCreated:
    annotation_label_id = _get_or_create_annotation_label_id(
        session=session, collection_id=collection_id, class_name=class_name
    )
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=session,
        collection_id=collection_id,
        sample_type=SampleType.ANNOTATION,
        name=annotation_collection_name,
    )

    # `annotation_resolver.create_many` commits, so every batch lands in its own
    # transaction. That is deliberate: the dedupe above makes the whole operation
    # idempotent, so a run that fails halfway is recovered by re-running it, which
    # skips whatever already landed. Do not collapse this into one transaction
    # expecting all-or-nothing semantics that nothing here relies on.
    created_annotation_ids: list[UUID] = []
    skipped_count = 0
    for start in range(0, len(parent_sample_ids), CREATE_BATCH_SIZE):
        batch = parent_sample_ids[start : start + CREATE_BATCH_SIZE]
        missing = _parent_sample_ids_without_label(
            session=session,
            parent_sample_ids=batch,
            annotation_label_id=annotation_label_id,
            annotation_collection_id=annotation_collection_id,
        )
        skipped_count += len(batch) - len(missing)
        if not missing:
            continue
        created_annotation_ids.extend(
            annotation_resolver.create_many(
                session=session,
                parent_collection_id=collection_id,
                annotations=[
                    AnnotationCreate(
                        annotation_label_id=annotation_label_id,
                        annotation_type=AnnotationType.CLASSIFICATION,
                        parent_sample_id=parent_sample_id,
                    )
                    for parent_sample_id in missing
                ],
                collection_name=annotation_collection_name,
            )
        )

    if created_annotation_ids:
        evaluation_run_resolver.mark_stale_by_collection_id(
            session=session, collection_id=annotation_collection_id
        )
    return ClassificationAnnotationsCreated(
        created_annotation_ids=created_annotation_ids,
        created_count=len(created_annotation_ids),
        skipped_count=skipped_count,
    )


def _parent_sample_ids_without_label(
    session: Session,
    parent_sample_ids: Sequence[UUID],
    annotation_label_id: UUID,
    annotation_collection_id: UUID,
) -> list[UUID]:
    existing = annotation_resolver.get_parent_sample_ids_with_label(
        session=session,
        parent_sample_ids=parent_sample_ids,
        annotation_label_id=annotation_label_id,
        annotation_collection_id=annotation_collection_id,
        annotation_type=AnnotationType.CLASSIFICATION,
    )
    return [
        parent_sample_id
        for parent_sample_id in parent_sample_ids
        if parent_sample_id not in existing
    ]


def _get_or_create_annotation_label_id(
    session: Session, collection_id: UUID, class_name: str
) -> UUID:
    collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
    if collection is None:
        raise ValueError(f"Collection with id {collection_id} not found.")

    label = annotation_label_resolver.get_by_label_name(
        session=session, dataset_id=collection.dataset_id, label_name=class_name
    )
    if label is None:
        label = annotation_label_resolver.create(
            session=session,
            label=AnnotationLabelCreate(
                dataset_id=collection.dataset_id, annotation_label_name=class_name
            ),
        )
    return label.annotation_label_id
