"""Get all annotations for the provided parent sample IDs."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, func, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoFrameTable, VideoTable


def get_all_by_parent_sample_ids(
    session: Session,
    parent_sample_ids: Sequence[UUID],
    annotation_type: AnnotationType | None = None,
    annotation_collection_id: UUID | None = None,
) -> Sequence[AnnotationBaseTable]:
    """Get all annotations belonging to the provided parent sample IDs.

    Args:
        session: SQLAlchemy session.
        parent_sample_ids: Parent sample IDs to fetch annotations for.
        annotation_type: If set, only annotations of this type are returned.
        annotation_collection_id: If set, only annotations belonging to this
            annotation collection are returned.
    """
    if not parent_sample_ids:
        return []
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
        .where(col(AnnotationBaseTable.parent_sample_id).in_(parent_sample_ids))
        .order_by(
            func.coalesce(ImageTable.file_path_abs, VideoTable.file_path_abs, "").asc(),
            col(AnnotationBaseTable.created_at).asc(),
            col(AnnotationBaseTable.sample_id).asc(),
        )
    )
    if annotation_type is not None:
        annotations_statement = annotations_statement.where(
            col(AnnotationBaseTable.annotation_type) == annotation_type
        )
    if annotation_collection_id is not None:
        annotations_statement = annotations_statement.join(
            SampleTable,
            col(SampleTable.sample_id) == col(AnnotationBaseTable.sample_id),
        ).where(col(SampleTable.collection_id) == annotation_collection_id)
    return session.exec(annotations_statement).all()
