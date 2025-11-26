"""Implementation of get_dimension_bounds function for images."""

from __future__ import annotations

from uuid import UUID

from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.models.dataset import SampleType
from lightly_studio.models.image import ImageTable
from sqlmodel import Session, col, func, select
from sqlmodel.sql.expression import Select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.tag import TagTable


def get_dimension_bounds(
    session: Session,
    dataset_id: UUID,
    annotation_label_ids: list[UUID] | None = None,
    tag_ids: list[UUID] | None = None,
    sample_type: SampleType = SampleType.IMAGE
) -> dict[str, int]:
    """Get min and max dimensions of samples in a dataset."""
    if sample_type == SampleType.IMAGE:
        dim_table = ImageTable
        ann_join_table = ImageTable
    else:
        dim_table = VideoTable
        ann_join_table = VideoFrameTable
        
    # Prepare the base query for dimensions
    query: Select[tuple[int | None, int | None, int | None, int | None]] = select(
        func.min(dim_table.width).label("min_width"),
        func.max(dim_table.width).label("max_width"),
        func.min(dim_table.height).label("min_height"),
        func.max(dim_table.height).label("max_height"),
    )
    query = query.join(dim_table.sample)

    if annotation_label_ids:
        # Subquery to filter samples matching all annotation labels
        label_filter = (
            select(dim_table.sample_id)
            .join(dim_table.sample)
            .join(
                AnnotationBaseTable,
                ann_join_table.sample_id == AnnotationBaseTable.parent_sample_id,
            )
            .join(
                AnnotationLabelTable,
                AnnotationBaseTable.annotation_label_id
                == AnnotationLabelTable.annotation_label_id,
            )
            .where(
                SampleTable.dataset_id == dataset_id,
                col(AnnotationLabelTable.annotation_label_id).in_(annotation_label_ids),
            )
            .group_by(dim_table.sample_id)
            .having(
                func.count(col(AnnotationLabelTable.annotation_label_id).distinct())
                == len(annotation_label_ids)
            )
        )
        # Filter the dimension query based on the subquery
        query = query.where(col(dim_table.sample_id).in_(label_filter))
    else:
        # If no labels specified, filter dimensions
        # for all samples in the dataset
        query = query.where(SampleTable.dataset_id == dataset_id)

    if tag_ids:
        query = (
            query.join(SampleTable.tags)
            .where(SampleTable.tags.any(col(TagTable.tag_id).in_(tag_ids)))
            .distinct()
        )

    # Note: We use SQLAlchemy's session.execute instead of SQLModel's
    # ession.exec to be able to fetch the columns with names with the
    # `mappings()` method.
    result = session.execute(query).mappings().one()
    return {key: value for key, value in result.items() if value is not None}
