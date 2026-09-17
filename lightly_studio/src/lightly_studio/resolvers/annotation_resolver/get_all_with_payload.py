"""Get all annotations with payload resolver."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.orm import aliased, joinedload, load_only
from sqlmodel import Session, col, func, select
from sqlmodel.sql.expression import Select

from lightly_studio.api.routes.api.validators import Paginated

# Aliased because `order_by` is also a local variable name in this module.
from lightly_studio.core.dataset_query import order_by as order_by_module
from lightly_studio.core.dataset_query.order_by import OrderByExpression
from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationView,
    AnnotationWithPayloadAndCountView,
    AnnotationWithPayloadView,
    ImageAnnotationView,
    SampleAnnotationView,
    VideoAnnotationView,
    VideoFrameAnnotationView,
)
from lightly_studio.models.collection import SampleType
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.resolvers import collection_resolver, embedding_region_resolver
from lightly_studio.resolvers.annotations import annotation_ordering
from lightly_studio.resolvers.annotations.annotations_filter import (
    AnnotationsFilter,
)
from lightly_studio.resolvers.similarity_utils import (
    apply_similarity_join,
    distance_to_similarity,
    get_distance_expression,
)


@dataclass
class AnnotationOrdering:
    """How annotations are ordered before the tiebreaker chain.

    Similarity search dominates: while ``text_embedding`` is set, ``order_by`` is ignored,
    as in the sample grid where the text query has to be cleared before another sort applies.

    Args:
        text_embedding: Optional embedding; when given, annotations are ordered by cosine
            distance of their embedding to it.
        order_by: Optional order by expression, e.g. an evaluation metric value.
    """

    text_embedding: list[float] | None = None
    order_by: OrderByExpression | None = None


def get_all_with_payload(
    session: Session,
    collection_id: UUID,
    pagination: Paginated | None = None,
    filters: AnnotationsFilter | None = None,
    ordering: AnnotationOrdering | None = None,
) -> AnnotationWithPayloadAndCountView:
    """Get all annotations with payload from the database.

    Args:
        session: Database session
        pagination: Optional pagination parameters
        filters: Optional filters to apply to the query
        collection_id: ID of the collection to get annotations for
        ordering: Optional ordering applied before the tiebreaker chain.

    Returns:
        List of annotations matching the filters with payload
    """
    ordering = ordering or AnnotationOrdering()
    parent_collection = collection_resolver.get_parent_collection_id(
        session=session, collection_id=collection_id
    )

    if parent_collection is None:
        raise ValueError(f"Collection with id {collection_id} does not have a parent collection.")

    sample_type = parent_collection.sample_type

    base_query = _build_base_query(sample_type=sample_type)

    if filters:
        if filters.embedding_region is not None:
            filters.region_sample_ids = embedding_region_resolver.get_sample_ids_in_region(
                session=session,
                collection_id=collection_id,
                region=filters.embedding_region,
            )
        base_query = filters.apply(base_query)

    embedding_model_id, distance_expr = get_distance_expression(
        session=session, collection_id=collection_id, text_embedding=ordering.text_embedding
    )
    order_by = ordering.order_by if distance_expr is None else None
    if distance_expr is not None:
        base_query = apply_similarity_join(
            query=base_query,
            sample_id_column=col(AnnotationBaseTable.sample_id),
            embedding_model_id=embedding_model_id,
        )

    # Sort joins stay out of the count query below: they cannot change the count, so joining
    # there would only run the join a second time per page. The type is loosened to Any
    # because the sort value and the similarity distance are appended as extra columns,
    # changing the row shape from a 2-tuple.
    rows_query: Any = base_query
    if order_by is not None:
        # Appends the sort value to the SELECT and orders by it, so the tiebreaker chain
        # below is appended after the sort key.
        rows_query = order_by.apply_with_order_value(rows_query)

    annotations_query: Any = rows_query.order_by(
        *annotation_ordering.build_order_by(
            file_path_abs=annotation_ordering.file_path_abs_expression(sample_type=sample_type),
            created_at=col(AnnotationBaseTable.created_at),
            annotation_sample_id=col(AnnotationBaseTable.sample_id),
            leading_order_key=distance_expr,
        ),
    )
    if distance_expr is not None:
        annotations_query = annotations_query.add_columns(distance_expr)

    total_count_query = select(func.count()).select_from(base_query.subquery())
    total_count = session.exec(total_count_query).one()

    if pagination is not None:
        annotations_query = annotations_query.offset(pagination.offset).limit(pagination.limit)

    next_cursor = None
    if pagination and pagination.offset + pagination.limit < total_count:
        next_cursor = pagination.offset + pagination.limit

    rows = session.exec(annotations_query).all()

    return AnnotationWithPayloadAndCountView(
        total_count=total_count,
        next_cursor=next_cursor,
        annotations=_build_annotation_views(
            rows=rows, sample_type=sample_type, has_distance=distance_expr is not None
        ),
    )


def _build_annotation_views(
    rows: Sequence[Any],
    sample_type: SampleType,
    has_distance: bool,
) -> list[AnnotationWithPayloadView]:
    """Turn query rows into views, unpacking the distance column when present.

    The sort value is read by label, so it is ``None`` whenever no sort is active.
    """
    annotation_views = []
    for row in rows:
        if has_distance:
            annotation, payload, distance = row
            similarity_score = distance_to_similarity(distance)
        else:
            annotation, payload = row[0], row[1]
            similarity_score = None
        annotation_views.append(
            AnnotationWithPayloadView(
                parent_sample_type=sample_type,
                annotation=AnnotationView.from_annotation_table(
                    annotation=annotation,
                    order_value=order_by_module.get_order_value(row=row),
                ),
                parent_sample_data=_serialize_annotation_payload(payload=payload),
                similarity_score=similarity_score,
            )
        )
    return annotation_views


def _build_base_query(
    sample_type: SampleType,
) -> Select[tuple[AnnotationBaseTable, Any]]:
    if sample_type == SampleType.IMAGE:
        # this alias is needed to avoid name clashes in joins
        SampleFromImage = aliased(SampleTable)  # noqa: N806

        return (
            select(AnnotationBaseTable, ImageTable)
            .join(
                ImageTable,
                col(ImageTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
            )
            .join(SampleFromImage, col(SampleFromImage.sample_id) == col(ImageTable.sample_id))
            .options(
                load_only(
                    ImageTable.file_path_abs,  # type: ignore[arg-type]
                    ImageTable.sample_id,  # type: ignore[arg-type]
                    ImageTable.height,  # type: ignore[arg-type]
                    ImageTable.width,  # type: ignore[arg-type]
                ),
                joinedload(ImageTable.sample).load_only(
                    SampleTable.collection_id,  # type: ignore[arg-type]
                ),
            )
        )

    if sample_type in (SampleType.VIDEO_FRAME, SampleType.VIDEO):
        return (
            select(AnnotationBaseTable, VideoFrameTable)
            .join(
                VideoFrameTable,
                col(VideoFrameTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
            )
            .join(VideoFrameTable.video)
            .options(
                load_only(VideoFrameTable.sample_id),  # type: ignore[arg-type]
                joinedload(VideoFrameTable.video).load_only(
                    VideoTable.height,  # type: ignore[arg-type]
                    VideoTable.width,  # type: ignore[arg-type]
                    VideoTable.file_path_abs,  # type: ignore[arg-type]
                ),
            )
        )

    raise NotImplementedError(f"Unsupported sample type: {sample_type}")


def _serialize_annotation_payload(
    payload: ImageTable | VideoFrameTable,
) -> ImageAnnotationView | VideoFrameAnnotationView:
    """Serialize annotation based on sample type."""
    if isinstance(payload, ImageTable):
        return ImageAnnotationView(
            height=payload.height,
            width=payload.width,
            file_path_abs=payload.file_path_abs,
            sample_id=payload.sample_id,
            sample=SampleAnnotationView(collection_id=payload.sample.collection_id),
        )

    if isinstance(payload, VideoFrameTable):
        return VideoFrameAnnotationView(
            sample_id=payload.sample_id,
            video=VideoAnnotationView(
                width=payload.video.width,
                height=payload.video.height,
                file_path_abs=payload.video.file_path_abs,
            ),
        )

    raise NotImplementedError("Unsupported sample type")
