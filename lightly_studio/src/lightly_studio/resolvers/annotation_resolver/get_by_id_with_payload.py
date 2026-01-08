"""Get annotation by id with payload resolver."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import aliased, joinedload, load_only
from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationDetailsWithPayloadView,
    AnnotationView,
    ImageAnnotationDetailsView,
    VideoFrameAnnotationDetailsView,
)
from lightly_studio.models.collection import SampleType
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.resolvers import collection_resolver


def get_by_id_with_payload(
    session: Session,
    sample_id: UUID,
) -> AnnotationDetailsWithPayloadView | None:
    """Get annotation by its id with payload from the database.

    Args:
        session: Database session
        sample_id: ID of the sample to get annotations for

    Returns:
        Returns annotations with payload
    """
    parent_collection = collection_resolver.get_parent_collection_by_sample_id(
        session=session, sample_id=sample_id
    )

    if parent_collection is None:
        raise ValueError(f"Sample with id {sample_id} does not have a parent collection.")

    parent_sample_type = parent_collection.sample_type

    if parent_sample_type in SampleType.VIDEO_FRAME:
        return _get_video_frame_annotation_by_id(
            session=session, sample_id=sample_id, parent_sample_type=parent_sample_type
        )
    if parent_sample_type == SampleType.IMAGE:
        return _get_image_annotation_by_id(session=session, sample_id=sample_id)

    raise NotImplementedError("Unsupported sample type")


SampleFromImage = aliased(SampleTable)


def _get_image_annotation_by_id(
    session: Session, sample_id: UUID
) -> AnnotationDetailsWithPayloadView | None:
    base_query = (
        select(AnnotationBaseTable, ImageTable)
        .join(
            ImageTable,
            col(ImageTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        )
        .join(SampleFromImage, col(SampleFromImage.sample_id) == col(ImageTable.sample_id))
        .options(
            load_only(
                ImageTable.file_path_abs,  # type: ignore[arg-type]
                ImageTable.file_name,  # type: ignore[arg-type]
                ImageTable.sample_id,  # type: ignore[arg-type]
                ImageTable.height,  # type: ignore[arg-type]
                ImageTable.width,  # type: ignore[arg-type]
            ),
        )
        .where(col(AnnotationBaseTable.sample_id) == sample_id)
    )

    row = session.exec(base_query).one_or_none()

    if row is None:
        return None

    (annotation, payload) = row

    return AnnotationDetailsWithPayloadView(
        parent_sample_type=SampleType.IMAGE,
        annotation=AnnotationView.model_validate(annotation),
        parent_sample_data=ImageAnnotationDetailsView.from_image_table(payload),
    )


def _get_video_frame_annotation_by_id(
    session: Session, sample_id: UUID, parent_sample_type: SampleType
) -> AnnotationDetailsWithPayloadView | None:
    base_query = (
        select(AnnotationBaseTable, VideoFrameTable)
        .join(
            VideoFrameTable,
            col(VideoFrameTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        )
        .join(VideoFrameTable.video)
        .options(
            load_only(
                VideoFrameTable.sample_id,  # type: ignore[arg-type]
                VideoFrameTable.frame_number,  # type: ignore[arg-type]
                VideoFrameTable.frame_timestamp_s,  # type: ignore[arg-type]
            ),
            joinedload(VideoFrameTable.video).load_only(
                VideoTable.height,  # type: ignore[arg-type]
                VideoTable.width,  # type: ignore[arg-type]
                VideoTable.file_path_abs,  # type: ignore[arg-type]
            ),
        )
        .where(col(AnnotationBaseTable.sample_id) == sample_id)
    )

    row = session.exec(base_query).one_or_none()

    if row is None:
        return None

    (annotation, payload) = row

    return AnnotationDetailsWithPayloadView(
        parent_sample_type=parent_sample_type,
        annotation=AnnotationView.model_validate(annotation),
        parent_sample_data=VideoFrameAnnotationDetailsView.from_video_frame_table(payload),
    )
