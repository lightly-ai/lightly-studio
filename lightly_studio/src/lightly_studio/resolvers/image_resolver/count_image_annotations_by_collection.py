"""Count image-scoped annotation label totals and filtered counts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import ColumnElement
from sqlalchemy.orm import aliased
from sqlmodel import Session, col, func, select
from sqlmodel.sql.expression import Select

from lightly_studio.database import db_array
from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationType,
)
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable, SampleTagLinkTable
from lightly_studio.models.tag import TagTable
from lightly_studio.resolvers import embedding_region_resolver
from lightly_studio.resolvers.image_filter import ImageFilter


class AnnotationCountMode(str, Enum):
    """Controls what the annotation count represents."""

    OBJECTS = "objects"
    SAMPLES = "samples"


@dataclass(frozen=True)
class AnnotationClassCount:
    """Annotation count for one class.

    Attributes:
        label_name: Annotation class name on the shared class axis.
        count: Number of matching annotation objects or distinct annotated samples.
    """

    label_name: str
    count: int


@dataclass(frozen=True)
class SampleTagAnnotationCounts:
    """Annotation class counts for one sample tag.

    Attributes:
        sample_tag_id: ID of the selected sample tag.
        sample_tag_name: Name of the selected sample tag.
        counts: Zero-filled counts on the shared class axis.
    """

    sample_tag_id: UUID
    sample_tag_name: str
    counts: list[AnnotationClassCount]


def count_image_annotations_by_sample_tags(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    sample_tag_ids: list[UUID],
    image_filter: ImageFilter | None = None,
    annotation_type: AnnotationType | None = None,
    count_mode: AnnotationCountMode = AnnotationCountMode.OBJECTS,
) -> list[SampleTagAnnotationCounts]:
    """Count image annotations independently for each requested sample tag.

    The active image filter is intersected with each sample tag. Annotation source
    restrictions inside the filter also scope the shared class axis.

    Args:
        session: Database session used to validate tags and execute count queries.
        collection_id: ID of the image collection whose annotations are counted.
        sample_tag_ids: Ordered sample tag IDs. Empty input returns no series.
        image_filter: Active image filter applied in addition to each sample tag.
        annotation_type: Optional annotation type restriction.
        count_mode: Whether to count annotation objects or distinct parent samples.

    Returns:
        One zero-filled class-count series per requested tag, preserving request order.

    Raises:
        ValueError: If a requested ID is not a sample tag in the target collection.
    """
    if not sample_tag_ids:
        return []

    sample_tags = _get_and_validate_sample_tags(
        session=session,
        collection_id=collection_id,
        sample_tag_ids=sample_tag_ids,
    )
    _resolve_embedding_region(
        session=session,
        collection_id=collection_id,
        image_filter=image_filter,
    )
    annotation_collection_ids = _get_annotation_collection_ids(image_filter=image_filter)
    class_names = list(
        _get_total_counts(
            session=session,
            collection_id=collection_id,
            annotation_type=annotation_type,
            count_mode=count_mode,
            annotation_collection_ids=annotation_collection_ids,
        )
    )
    grouped_counts = _get_counts_grouped_by_sample_tag(
        session=session,
        collection_id=collection_id,
        sample_tag_ids=sample_tag_ids,
        image_filter=image_filter,
        annotation_type=annotation_type,
        annotation_collection_ids=annotation_collection_ids,
        count_mode=count_mode,
    )
    return _build_sample_tag_counts(
        sample_tag_ids=sample_tag_ids,
        sample_tags=sample_tags,
        class_names=class_names,
        grouped_counts=grouped_counts,
    )


def count_image_annotations_by_collection(
    session: Session,
    collection_id: UUID,
    image_filter: ImageFilter | None = None,
    annotation_type: AnnotationType | None = None,
    count_mode: AnnotationCountMode = AnnotationCountMode.OBJECTS,
) -> list[tuple[str, int, int]]:
    """Count annotations for a specific image collection.

    Annotations for a specific collection are grouped by annotation
    label name and counted for total and filtered.
    Returns a list of (label_name, current_count, total_count) tuples.

    When ``annotation_type`` is provided, both the total and filtered counts are
    restricted to annotations of that type (e.g. only CLASSIFICATION or only
    OBJECT_DETECTION).

    When ``count_mode`` is ``OBJECTS`` (default), each annotation row is counted
    individually.  When ``count_mode`` is ``SAMPLES``, the count reflects the
    number of distinct parent samples that carry at least one matching annotation,
    so a sample with multiple annotations of the same label is counted only once.

    When a subset of annotation source collections is selected (via the filter's
    ``annotations_filter.collection_ids``), both the total and filtered counts are
    restricted to those sources. Annotations from unselected sources are excluded
    from the total as well, so the total never counts labels the current view does
    not care about (e.g. viewing a single source shows "2 of 2", not "2 of 4").
    """
    _resolve_embedding_region(
        session=session,
        collection_id=collection_id,
        image_filter=image_filter,
    )
    annotation_collection_ids = _get_annotation_collection_ids(image_filter=image_filter)
    total_counts = _get_total_counts(
        session=session,
        collection_id=collection_id,
        annotation_type=annotation_type,
        count_mode=count_mode,
        annotation_collection_ids=annotation_collection_ids,
    )
    current_counts = _get_current_counts(
        session=session,
        collection_id=collection_id,
        image_filter=image_filter,
        annotation_type=annotation_type,
        annotation_collection_ids=annotation_collection_ids,
        count_mode=count_mode,
    )

    return [
        (label, current_counts.get(label, 0), total_count)
        for label, total_count in total_counts.items()
    ]


def _get_and_validate_sample_tags(
    session: Session,
    collection_id: UUID,
    sample_tag_ids: list[UUID],
) -> dict[UUID, str]:
    query = select(TagTable.tag_id, TagTable.name).where(
        col(TagTable.collection_id) == collection_id,
        col(TagTable.kind) == "sample",
        db_array.in_array(column=col(TagTable.tag_id), values=sample_tag_ids),
    )
    sample_tags = dict(session.exec(query).all())
    invalid_ids = set(sample_tag_ids) - sample_tags.keys()
    if invalid_ids:
        ids = ", ".join(sorted(str(tag_id) for tag_id in invalid_ids))
        raise ValueError(
            f"Tags must be sample tags belonging to collection {collection_id}: {ids}."
        )
    return sample_tags


def _resolve_embedding_region(
    session: Session,
    collection_id: UUID,
    image_filter: ImageFilter | None,
) -> None:
    """Resolve an embedding region to sample IDs before applying the image filter."""
    sample_filter = image_filter.sample_filter if image_filter is not None else None
    if sample_filter is None or sample_filter.embedding_region is None:
        return
    sample_filter.region_sample_ids = embedding_region_resolver.get_sample_ids_in_region(
        session=session,
        collection_id=collection_id,
        region=sample_filter.embedding_region,
    )


def _get_annotation_collection_ids(image_filter: ImageFilter | None) -> list[UUID] | None:
    sample_filter = image_filter.sample_filter if image_filter is not None else None
    if sample_filter is None or sample_filter.annotations_filter is None:
        return None
    return sample_filter.annotations_filter.collection_ids


def _build_count_expression(count_mode: AnnotationCountMode) -> ColumnElement[int]:
    if count_mode == AnnotationCountMode.SAMPLES:
        return func.count(func.distinct(col(AnnotationBaseTable.parent_sample_id)))
    return func.count(col(AnnotationBaseTable.sample_id))


_SelectRow = TypeVar("_SelectRow")


def _restrict_to_annotation_sources(
    query: Select[_SelectRow],
    annotation_collection_ids: list[UUID],
) -> Select[_SelectRow]:
    """Restrict the counted annotations to the given source collections.

    The annotation's own sample (aliased to avoid clashing with the image sample
    joined by the caller) carries its collection id.
    """
    annotation_sample = aliased(SampleTable)
    return query.join(
        annotation_sample,
        col(annotation_sample.sample_id) == col(AnnotationBaseTable.sample_id),
    ).where(
        db_array.in_array(
            column=col(annotation_sample.collection_id),
            values=annotation_collection_ids,
        )
    )


def _get_counts_grouped_by_sample_tag(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    sample_tag_ids: list[UUID],
    image_filter: ImageFilter | None,
    annotation_type: AnnotationType | None,
    annotation_collection_ids: list[UUID] | None,
    count_mode: AnnotationCountMode,
) -> dict[tuple[UUID, str], int]:
    query: Any = (
        select(
            SampleTagLinkTable.tag_id,
            AnnotationLabelTable.annotation_label_name,
            _build_count_expression(count_mode).label("count"),
        )
        .join(
            AnnotationBaseTable,
            col(AnnotationBaseTable.annotation_label_id)
            == col(AnnotationLabelTable.annotation_label_id),
        )
        .join(
            ImageTable,
            col(ImageTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        )
        .join(SampleTable, col(SampleTable.sample_id) == col(ImageTable.sample_id))
        .join(
            SampleTagLinkTable,
            col(SampleTagLinkTable.sample_id) == col(SampleTable.sample_id),
        )
        .where(
            col(SampleTable.collection_id) == collection_id,
            db_array.in_array(column=col(SampleTagLinkTable.tag_id), values=sample_tag_ids),
        )
    )
    if annotation_type is not None:
        query = query.where(col(AnnotationBaseTable.annotation_type) == annotation_type)
    if annotation_collection_ids:
        query = _restrict_to_annotation_sources(query, annotation_collection_ids)
    if image_filter is not None:
        query = image_filter.apply(query)
    query = query.group_by(
        col(SampleTagLinkTable.tag_id),
        AnnotationLabelTable.annotation_label_name,
    )
    result: dict[tuple[UUID, str], int] = {}
    for tag_id, label_name, count in session.exec(query).all():
        assert tag_id is not None
        result[(tag_id, label_name)] = count
    return result


def _build_sample_tag_counts(
    sample_tag_ids: list[UUID],
    sample_tags: dict[UUID, str],
    class_names: list[str],
    grouped_counts: dict[tuple[UUID, str], int],
) -> list[SampleTagAnnotationCounts]:
    return [
        SampleTagAnnotationCounts(
            sample_tag_id=tag_id,
            sample_tag_name=sample_tags[tag_id],
            counts=[
                AnnotationClassCount(
                    label_name=class_name,
                    count=grouped_counts.get((tag_id, class_name), 0),
                )
                for class_name in class_names
            ],
        )
        for tag_id in sample_tag_ids
    ]


def _get_total_counts(
    session: Session,
    collection_id: UUID,
    annotation_type: AnnotationType | None = None,
    count_mode: AnnotationCountMode = AnnotationCountMode.OBJECTS,
    annotation_collection_ids: list[UUID] | None = None,
) -> dict[str, int]:
    """Returns total annotation counts per label for the collection."""
    total_counts_query = (
        select(
            AnnotationLabelTable.annotation_label_name,
            _build_count_expression(count_mode).label("total_count"),
        )
        .join(
            AnnotationBaseTable,
            col(AnnotationBaseTable.annotation_label_id)
            == col(AnnotationLabelTable.annotation_label_id),
        )
        .join(
            ImageTable,
            col(ImageTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        )
        .join(
            SampleTable,
            col(SampleTable.sample_id) == col(ImageTable.sample_id),
        )
        .where(SampleTable.collection_id == collection_id)
    )

    if annotation_type is not None:
        total_counts_query = total_counts_query.where(
            col(AnnotationBaseTable.annotation_type) == annotation_type
        )

    if annotation_collection_ids:
        total_counts_query = _restrict_to_annotation_sources(
            total_counts_query, annotation_collection_ids
        )

    total_counts_query = total_counts_query.group_by(
        AnnotationLabelTable.annotation_label_name
    ).order_by(col(AnnotationLabelTable.annotation_label_name).asc())

    return {row[0]: row[1] for row in session.exec(total_counts_query).all()}


def _get_current_counts(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    image_filter: ImageFilter | None,
    annotation_type: AnnotationType | None = None,
    annotation_collection_ids: list[UUID] | None = None,
    count_mode: AnnotationCountMode = AnnotationCountMode.OBJECTS,
) -> dict[str, int]:
    """Returns filtered annotation counts per label for the collection."""
    filtered_query = (
        select(
            AnnotationLabelTable.annotation_label_name,
            _build_count_expression(count_mode).label("current_count"),
        )
        .join(
            AnnotationBaseTable,
            col(AnnotationBaseTable.annotation_label_id)
            == col(AnnotationLabelTable.annotation_label_id),
        )
        .join(
            ImageTable,
            col(ImageTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        )
        .join(
            SampleTable,
            col(SampleTable.sample_id) == col(ImageTable.sample_id),
        )
        .where(SampleTable.collection_id == collection_id)
    )

    if annotation_type is not None:
        filtered_query = filtered_query.where(
            col(AnnotationBaseTable.annotation_type) == annotation_type
        )

    # Restrict the counted annotations to the selected source collections.
    if annotation_collection_ids:
        filtered_query = _restrict_to_annotation_sources(filtered_query, annotation_collection_ids)

    if image_filter is not None:
        filtered_query = image_filter.apply(filtered_query)

    # Group by label name and sort
    filtered_query = filtered_query.group_by(AnnotationLabelTable.annotation_label_name).order_by(
        col(AnnotationLabelTable.annotation_label_name).asc()
    )

    rows = session.exec(filtered_query).all()
    return {row[0]: row[1] for row in rows}
