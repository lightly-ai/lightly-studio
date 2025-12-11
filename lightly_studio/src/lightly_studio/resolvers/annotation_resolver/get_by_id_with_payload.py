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
from lightly_studio.resolvers import dataset_resolver


def get_by_id_with_payload(
    session: Session,
    sample_id: UUID,
    dataset_id: UUID,
) -> AnnotationDetailsWithPayloadView | None:
    """Get annotation by its id with payload from the database.

    Args:
        session: Database session
        sample_id: ID of the sample to get annotations for
        dataset_id: The annotation dataset ID

    Returns:
        Returns annotations with payload
    """
    parent_dataset = dataset_resolver.get_parent_dataset_id(session=session, dataset_id=dataset_id)

    if parent_dataset is None:
        raise ValueError(f"Dataset with id {dataset_id} does not have a parent dataset.")

    sample_type = parent_dataset.sample_type

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
                    ImageTable.file_name,  # type: ignore[arg-type]
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
            file_name=payload.file_name,
            sample_id=payload.sample_id,
            sample=_serialize_sample_payload(payload.sample),
        )

    if isinstance(payload, VideoFrameTable):
        return VideoFrameAnnotationDetailsView(
            sample_id=payload.sample_id,
            frame_number=payload.frame_number,
            frame_timestamp_s=payload.frame_timestamp_s,
            video=VideoAnnotationView(
                width=payload.video.width,
                height=payload.video.height,
                file_path_abs=payload.video.file_path_abs,
            ),
            sample=_serialize_sample_payload(payload.sample),
        )

    raise NotImplementedError("Unsupported sample type")


def _serialize_sample_payload(sample: SampleTable) -> SampleAnnotationDetailsView:
    return SampleAnnotationDetailsView(
        sample_id=sample.sample_id,
        tags=sample.tags,
        dataset_id=sample.dataset_id,
    )
