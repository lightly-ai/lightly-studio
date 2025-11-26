"""Implementation of get_dimension_bounds function for images."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, func, select
from sqlmodel.sql.expression import Select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.dataset import SampleType
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.tag import TagTable
from lightly_studio.models.video import VideoFrameTable, VideoTable


def get_dimension_bounds(
    session: Session,
    dataset_id: UUID,
    annotation_label_ids: list[UUID] | None = None,
    tag_ids: list[UUID] | None = None,
    sample_type: SampleType = SampleType.IMAGE,
) -> dict[str, int]:
    """Get min and max dimensions of samples in a dataset."""
    query: Select[tuple[int | None, int | None, int | None, int | None]] = select(
        func.min(ImageTable.width).label("min_width")
        if sample_type == SampleType.IMAGE
        else func.min(VideoTable.width).label("min_width"),
        func.max(ImageTable.width).label("max_width")
        if sample_type == SampleType.IMAGE
        else func.max(VideoTable.width).label("max_width"),
        func.min(ImageTable.height).label("min_height")
        if sample_type == SampleType.IMAGE
        else func.min(VideoTable.height).label("min_height"),
        func.max(ImageTable.height).label("max_height")
        if sample_type == SampleType.IMAGE
        else func.max(VideoTable.height).label("max_height"),
    )

    query = query.join(SampleTable)

    if annotation_label_ids:
        label_filter = (
            select(
                ImageTable.sample_id if sample_type == SampleType.IMAGE else VideoTable.sample_id
            )
            .join(SampleTable)
            .join(
                AnnotationBaseTable,
                (
                    col(ImageTable.sample_id)
                    if sample_type == SampleType.IMAGE
                    else col(VideoFrameTable.sample_id)
                )
                == AnnotationBaseTable.parent_sample_id,
            )
            .join(
                AnnotationLabelTable,
                col(AnnotationBaseTable.annotation_label_id)
                == AnnotationLabelTable.annotation_label_id,
            )
            .where(
                SampleTable.dataset_id == dataset_id,
                col(AnnotationLabelTable.annotation_label_id).in_(annotation_label_ids),
            )
            .group_by(
                col(
                    ImageTable.sample_id
                    if sample_type == SampleType.IMAGE
                    else VideoTable.sample_id
                )
            )
            .having(
                func.count(col(AnnotationLabelTable.annotation_label_id).distinct())
                == len(annotation_label_ids)
            )
        )

        query = query.where(
            col(
                ImageTable.sample_id if sample_type == SampleType.IMAGE else VideoTable.sample_id
            ).in_(label_filter)
        )

    else:
        query = query.where(SampleTable.dataset_id == dataset_id)

    if tag_ids:
        query = (
            query.join(SampleTable.tags)
            .where(SampleTable.tags.any(col(TagTable.tag_id).in_(tag_ids)))
            .distinct()
        )

    result = session.execute(query).mappings().one()
    return {key: value for key, value in result.items() if value is not None}
