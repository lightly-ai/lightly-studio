"""Get all annotations for the provided parent sample IDs."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, func, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_layer import AnnotationLayerTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.video import VideoFrameTable, VideoTable


def get_all_by_parent_sample_ids(
    session: Session,
    parent_sample_ids: Sequence[UUID],
) -> Sequence[AnnotationBaseTable]:
    """Get all annotations belonging to the provided parent sample IDs."""
    annotations_statement = (
        select(AnnotationBaseTable)
        .outerjoin(
            ImageTable,
            col(ImageTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        )
        .outerjoin(
            VideoFrameTable,
            col(VideoFrameTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        )
        .outerjoin(VideoTable, col(VideoTable.sample_id) == col(VideoFrameTable.parent_sample_id))
        .outerjoin(
            AnnotationLayerTable,
            col(AnnotationLayerTable.annotation_id) == col(AnnotationBaseTable.sample_id),
        )
        .where(col(AnnotationBaseTable.parent_sample_id).in_(parent_sample_ids))
        .order_by(
            func.coalesce(ImageTable.file_path_abs, VideoTable.file_path_abs, "").asc(),
            func.coalesce(col(AnnotationLayerTable.position), 0).desc(),
            col(AnnotationBaseTable.created_at).desc(),
            col(AnnotationBaseTable.sample_id).asc(),
        )
    )
    return session.exec(annotations_statement).all()
