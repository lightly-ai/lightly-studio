"""Get all annotations for the provided parent sample IDs."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.orm import joinedload
from sqlmodel import Session, col, select

from lightly_studio.database import db_array
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.resolvers.annotations import annotation_ordering


def get_all_by_parent_sample_ids(
    session: Session,
    parent_sample_ids: Sequence[UUID],
) -> Sequence[AnnotationBaseTable]:
    """Get all annotations belonging to the provided parent sample IDs."""
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
        .where(
            db_array.in_array(
                column=col(AnnotationBaseTable.parent_sample_id), values=parent_sample_ids
            )
        )
        .order_by(
            *annotation_ordering.build_order_by(
                file_path_abs=annotation_ordering.coalesced_file_path_abs_expression(),
                created_at=col(AnnotationBaseTable.created_at),
                annotation_sample_id=col(AnnotationBaseTable.sample_id),
            )
        )
        .options(joinedload(AnnotationBaseTable.sample).load_only(SampleTable.collection_id))  # type: ignore[arg-type]
    )
    return session.exec(annotations_statement).all()
