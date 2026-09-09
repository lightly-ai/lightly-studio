"""Bulk-create classification annotations."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
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
from lightly_studio.resolvers import (
    annotation_label_resolver,
    collection_resolver,
    evaluation_run_resolver,
)
from lightly_studio.resolvers.annotation_resolver import create_many
from lightly_studio.utils import batching


class BulkCreateClassificationsResult(BaseModel):
    """Result of a bulk classification create operation."""

    created_annotation_ids: list[UUID]
    created_count: int
    skipped_count: int


@dataclass(frozen=True)
class _ClassificationCreateContext:
    parent_collection_id: UUID
    annotation_label_id: UUID
    annotation_collection_id: UUID
    annotation_collection_name: str | None


def bulk_create_classifications(
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
    annotation_collection_id = collection_resolver.get_or_create_child_collection(
        session=session,
        collection_id=parent_collection_id,
        sample_type=SampleType.ANNOTATION,
        name=annotation_collection_name,
    )
    context = _ClassificationCreateContext(
        parent_collection_id=parent_collection_id,
        annotation_label_id=annotation_label_id,
        annotation_collection_id=annotation_collection_id,
        annotation_collection_name=annotation_collection_name,
    )
    created_annotation_ids: list[UUID] = []
    skipped_count = 0

    for parent_sample_ids in _iter_parent_sample_id_pages(
        session=session,
        parent_sample_ids_query=parent_sample_ids_query,
    ):
        result = _bulk_create_classifications_for_source(
            session=session,
            parent_sample_ids=parent_sample_ids,
            context=context,
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


def _iter_parent_sample_id_pages(
    session: Session,
    parent_sample_ids_query: SelectOfScalar[UUID],
) -> Iterator[list[UUID]]:
    """Yield the sample ids matched by the query in pages of bounded size.

    Every page is read with its own statement, so that writes between two pages cannot
    interfere with an open cursor. Pages are keyset-based: the next page starts after the
    last id of the previous one, which stays correct even when the writes change which
    samples the query matches.

    Args:
        session: SQLAlchemy session for database operations.
        parent_sample_ids_query: Query selecting the parent sample ids to page through.

    Yields:
        Pages of sample ids, ordered by sample id.
    """
    last_parent_sample_id: UUID | None = None
    while True:
        page_query = select(SampleTable.sample_id).where(
            col(SampleTable.sample_id).in_(parent_sample_ids_query)
        )
        if last_parent_sample_id is not None:
            page_query = page_query.where(col(SampleTable.sample_id) > last_parent_sample_id)
        parent_sample_ids = list(
            session.exec(
                page_query.order_by(col(SampleTable.sample_id)).limit(batching.DEFAULT_BATCH_SIZE)
            ).all()
        )
        if not parent_sample_ids:
            return
        yield parent_sample_ids
        last_parent_sample_id = parent_sample_ids[-1]


def _bulk_create_classifications_for_source(
    session: Session,
    parent_sample_ids: list[UUID],
    context: _ClassificationCreateContext,
) -> BulkCreateClassificationsResult:
    existing_parent_sample_ids = _get_existing_classification_parent_sample_ids(
        session=session,
        parent_sample_ids=parent_sample_ids,
        annotation_label_id=context.annotation_label_id,
        annotation_collection_id=context.annotation_collection_id,
    )
    annotations = [
        AnnotationCreate(
            annotation_label_id=context.annotation_label_id,
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
        parent_collection_id=context.parent_collection_id,
        annotations=annotations,
        collection_name=context.annotation_collection_name,
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
    collection = collection_resolver.get_by_id(session=session, collection_id=parent_collection_id)
    if collection is None:
        raise ValueError(f"Collection with id {parent_collection_id} not found.")

    label = annotation_label_resolver.get_by_label_name(
        session=session,
        dataset_id=collection.dataset_id,
        label_name=class_name,
    )
    if label is not None:
        return label.annotation_label_id

    return annotation_label_resolver.create(
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

    evaluation_run_resolver.mark_stale_by_collection_id(
        session=session,
        collection_id=annotation_collection_id,
    )
