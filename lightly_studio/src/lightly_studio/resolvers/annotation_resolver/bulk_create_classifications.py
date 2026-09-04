"""Bulk-create classification annotations."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationCreate,
    AnnotationType,
)
from lightly_studio.models.annotation_label import AnnotationLabelCreate
from lightly_studio.models.collection import SampleType
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.annotation_label_resolver import create as create_annotation_label
from lightly_studio.resolvers.annotation_label_resolver import get_by_label_name
from lightly_studio.resolvers.annotation_resolver import create_many
from lightly_studio.resolvers.collection_resolver import get_by_id, get_or_create_child_collection
from lightly_studio.resolvers.evaluation_run_resolver import mark_stale_by_collection_id
from lightly_studio.utils import batching


class BulkCreateClassificationsResult(BaseModel):
    """Result of a bulk classification create operation."""

    created_annotation_ids: list[UUID]
    created_count: int
    skipped_count: int


def bulk_create_classifications(
    session: Session,
    parent_collection_id: UUID,
    parent_sample_ids: list[UUID],
    class_name: str,
    annotation_collection_name: str | None = None,
) -> BulkCreateClassificationsResult:
    """Create classification annotations for parent samples, skipping duplicates."""
    annotation_label_id = _get_or_create_annotation_label_id(
        session=session,
        parent_collection_id=parent_collection_id,
        class_name=class_name,
    )
    unique_parent_sample_ids = list(dict.fromkeys(parent_sample_ids))
    annotation_collection_id = get_or_create_child_collection(
        session=session,
        collection_id=parent_collection_id,
        sample_type=SampleType.ANNOTATION,
        name=annotation_collection_name,
    )
    result = _bulk_create_classifications_for_source(
        session=session,
        parent_collection_id=parent_collection_id,
        parent_sample_ids=unique_parent_sample_ids,
        annotation_label_id=annotation_label_id,
        annotation_collection_id=annotation_collection_id,
        annotation_collection_name=annotation_collection_name,
    )
    _mark_stale_if_changed(
        session=session,
        annotation_collection_id=annotation_collection_id,
        result=result,
    )
    return result


def bulk_create_classifications_from_query(
    session: Session,
    parent_collection_id: UUID,
    parent_sample_ids_query: SelectOfScalar[UUID],
    class_name: str,
    annotation_collection_name: str | None = None,
) -> BulkCreateClassificationsResult:
    """Create classification annotations for all parent samples returned by a query."""
    annotation_label_id = _get_or_create_annotation_label_id(
        session=session,
        parent_collection_id=parent_collection_id,
        class_name=class_name,
    )
    annotation_collection_id = get_or_create_child_collection(
        session=session,
        collection_id=parent_collection_id,
        sample_type=SampleType.ANNOTATION,
        name=annotation_collection_name,
    )
    created_annotation_ids: list[UUID] = []
    skipped_count = 0

    for parent_sample_ids in batching.batched(session.exec(parent_sample_ids_query).all()):
        # `create_many` commits internally, so each batch is its own transaction. This is
        # acceptable because dedupe makes a failed run recoverable by retrying the request.
        result = _bulk_create_classifications_for_source(
            session=session,
            parent_collection_id=parent_collection_id,
            parent_sample_ids=parent_sample_ids,
            annotation_label_id=annotation_label_id,
            annotation_collection_id=annotation_collection_id,
            annotation_collection_name=annotation_collection_name,
        )
        created_annotation_ids.extend(result.created_annotation_ids)
        skipped_count += result.skipped_count

    result = BulkCreateClassificationsResult(
        created_annotation_ids=created_annotation_ids,
        created_count=len(created_annotation_ids),
        skipped_count=skipped_count,
    )
    _mark_stale_if_changed(
        session=session,
        annotation_collection_id=annotation_collection_id,
        result=result,
    )
    return result


def _bulk_create_classifications_for_source(  # noqa: PLR0913
    session: Session,
    parent_collection_id: UUID,
    parent_sample_ids: list[UUID],
    annotation_label_id: UUID,
    annotation_collection_id: UUID,
    annotation_collection_name: str | None,
) -> BulkCreateClassificationsResult:
    existing_parent_sample_ids = _get_existing_classification_parent_sample_ids(
        session=session,
        parent_sample_ids=parent_sample_ids,
        annotation_label_id=annotation_label_id,
        annotation_collection_id=annotation_collection_id,
    )
    annotations = [
        AnnotationCreate(
            annotation_label_id=annotation_label_id,
            annotation_type=AnnotationType.CLASSIFICATION,
            parent_sample_id=parent_sample_id,
        )
        for parent_sample_id in parent_sample_ids
        if parent_sample_id not in existing_parent_sample_ids
    ]
    if not annotations:
        return BulkCreateClassificationsResult(
            created_annotation_ids=[],
            created_count=0,
            skipped_count=len(parent_sample_ids),
        )

    created_annotation_ids = create_many.create_many(
        session=session,
        parent_collection_id=parent_collection_id,
        annotations=annotations,
        collection_name=annotation_collection_name,
    )
    return BulkCreateClassificationsResult(
        created_annotation_ids=created_annotation_ids,
        created_count=len(created_annotation_ids),
        skipped_count=len(parent_sample_ids) - len(created_annotation_ids),
    )


def _get_existing_classification_parent_sample_ids(
    session: Session,
    parent_sample_ids: list[UUID],
    annotation_label_id: UUID,
    annotation_collection_id: UUID,
) -> set[UUID]:
    existing_parent_sample_ids: set[UUID] = set()
    for parent_sample_id_batch in batching.batched(parent_sample_ids):
        existing_parent_sample_ids.update(
            session.exec(
                select(AnnotationBaseTable.parent_sample_id)
                .join(SampleTable, col(AnnotationBaseTable.sample_id) == col(SampleTable.sample_id))
                .where(col(AnnotationBaseTable.parent_sample_id).in_(parent_sample_id_batch))
                .where(AnnotationBaseTable.annotation_label_id == annotation_label_id)
                .where(AnnotationBaseTable.annotation_type == AnnotationType.CLASSIFICATION)
                .where(SampleTable.collection_id == annotation_collection_id)
            ).all()
        )
    return existing_parent_sample_ids


def _get_or_create_annotation_label_id(
    session: Session,
    parent_collection_id: UUID,
    class_name: str,
) -> UUID:
    collection = get_by_id(session=session, collection_id=parent_collection_id)
    if collection is None:
        raise ValueError(f"Collection with id {parent_collection_id} not found.")

    label = get_by_label_name(
        session=session,
        dataset_id=collection.dataset_id,
        label_name=class_name,
    )
    if label is not None:
        return label.annotation_label_id

    return create_annotation_label(
        session=session,
        label=AnnotationLabelCreate(
            dataset_id=collection.dataset_id,
            annotation_label_name=class_name,
        ),
    ).annotation_label_id


def _mark_stale_if_changed(
    session: Session,
    annotation_collection_id: UUID,
    result: BulkCreateClassificationsResult,
) -> None:
    if not result.created_annotation_ids:
        return

    mark_stale_by_collection_id(
        session=session,
        collection_id=annotation_collection_id,
    )
