"""Get all annotations with payload resolver."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import aliased, joinedload, load_only
from sqlmodel import Session, col, func, select
from sqlmodel.sql.expression import Select

from lightly_studio.api.routes.api.validators import Paginated
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
from lightly_studio.resolvers import collection_resolver
from lightly_studio.resolvers.annotations.annotations_filter import (
    AnnotationsFilter,
)


def get_all_with_payload(
    session: Session,
    collection_id: UUID,
    pagination: Paginated | None = None,
    filters: AnnotationsFilter | None = None,
) -> AnnotationWithPayloadAndCountView:
    """Get all annotations with payload from the database.

    Args:
        session: Database session
        pagination: Optional pagination parameters
        filters: Optional filters to apply to the query
        collection_id: ID of the collection to get annotations for

    Returns:
        List of annotations matching the filters with payload
    """
    parent_collection = collection_resolver.get_parent_collection_id(
        session=session, collection_id=collection_id
    )

    if parent_collection is None:
        raise ValueError(f"Collection with id {collection_id} does not have a parent collection.")

    sample_type = parent_collection.sample_type

    base_query = _build_base_query(sample_type=sample_type)

    if filters:
        base_query = filters.apply(base_query)

    annotations_query = base_query.order_by(
        *_extra_order_by(sample_type=sample_type),
        col(AnnotationBaseTable.created_at).asc(),
        col(AnnotationBaseTable.sample_id).asc(),
    )

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
        annotations=[
            AnnotationWithPayloadView(
                parent_sample_type=sample_type,
                annotation=AnnotationView.model_validate(annotation),
                parent_sample_data=_serialize_annotation_payload(payload),
            )
            for annotation, payload in rows
        ],
    )


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


def _extra_order_by(sample_type: SampleType) -> list[Any]:
    """Return extra order by clauses for the query."""
    if sample_type == SampleType.IMAGE:
        return [
            col(ImageTable.file_path_abs).asc(),
        ]

    if sample_type in (SampleType.VIDEO_FRAME, SampleType.VIDEO):
        return [
            col(VideoTable.file_path_abs).asc(),
        ]

    return []


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
