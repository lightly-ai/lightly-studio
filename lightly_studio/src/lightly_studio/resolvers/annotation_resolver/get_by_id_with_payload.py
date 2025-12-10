"""Get annotation by id with payload resolver."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import aliased, joinedload, load_only
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import Select

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationDetailsWithPayloadView,
    ImageAnnotationDetailsView,
    SampleAnnotationDetailsView,
    VideoAnnotationView,
    VideoFrameAnnotationDetailsView,
)
from lightly_studio.models.dataset import SampleType
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoFrameTable, VideoTable


def get_by_id_with_payload(
    session: Session,
    sample_id: UUID,
    sample_type: SampleType,
) -> AnnotationDetailsWithPayloadView | None:
    """Get annotation by its id with payload from the database.

    Args:
        session: Database session
        sample_id: ID of the sample to get annotations for
        sample_type: Type of the sample (image, video frame, etc.)

    Returns:
        Returns annotations with payload
    """
    base_query = _build_base_query(sample_type=sample_type)

    base_query = base_query.where(col(AnnotationBaseTable.sample_id) == sample_id)

    row = session.exec(base_query).one_or_none()

    if row is None:
        return None

    return AnnotationDetailsWithPayloadView(
        parent_sample_type=sample_type,
        annotation=row[0],
        parent_sample_data=_serialize_annotation_payload(row[1]),
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
) -> ImageAnnotationDetailsView | VideoFrameAnnotationDetailsView:
    """Serialize annotation based on sample type."""
    if isinstance(payload, ImageTable):
        return ImageAnnotationDetailsView(
            height=payload.height,
            width=payload.width,
            file_path_abs=payload.file_path_abs,
            sample_id=payload.sample_id,
            sample=SampleAnnotationDetailsView(
                sample_id=payload.sample.sample_id,
                tags=payload.sample.tags,
                metadata_dict=payload.sample.metadata_dict,
            ),
        )

    if isinstance(payload, VideoFrameTable):
        return VideoFrameAnnotationDetailsView(
            sample_id=payload.sample_id,
            video=VideoAnnotationView(
                width=payload.video.width,
                height=payload.video.height,
                file_path_abs=payload.video.file_path_abs,
            ),
            sample=SampleAnnotationDetailsView(
                sample_id=payload.sample.sample_id,
                tags=payload.sample.tags,
                metadata_dict=payload.sample.metadata_dict,
            ),
        )

    raise NotImplementedError("Unsupported sample type")
