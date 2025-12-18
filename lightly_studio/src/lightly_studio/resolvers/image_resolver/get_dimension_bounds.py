"""Implementation of get_dimension_bounds function for images."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, func, select
from sqlmodel.sql.expression import Select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.tag import TagTable


def get_dimension_bounds(
    session: Session,
    collection_id: UUID,
    annotation_label_ids: list[UUID] | None = None,
    tag_ids: list[UUID] | None = None,
) -> dict[str, int]:
    """Get min and max dimensions of samples in a collection."""
    # Prepare the base query for dimensions
    query: Select[tuple[int | None, int | None, int | None, int | None]] = select(
        func.min(ImageTable.width).label("min_width"),
        func.max(ImageTable.width).label("max_width"),
        func.min(ImageTable.height).label("min_height"),
        func.max(ImageTable.height).label("max_height"),
    )
    query = query.join(ImageTable.sample)

    if annotation_label_ids:
        # Subquery to filter samples matching all annotation labels
        label_filter = (
            select(ImageTable.sample_id)
            .join(ImageTable.sample)
            .join(
                AnnotationBaseTable,
                col(ImageTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
            )
            .join(
                AnnotationLabelTable,
                col(AnnotationBaseTable.annotation_label_id)
                == col(AnnotationLabelTable.annotation_label_id),
            )
            .where(
                SampleTable.collection_id == collection_id,
                col(AnnotationLabelTable.annotation_label_id).in_(annotation_label_ids),
            )
            .group_by(col(ImageTable.sample_id))
            .having(
                func.count(col(AnnotationLabelTable.annotation_label_id).distinct())
                == len(annotation_label_ids)
            )
        )
        # Filter the dimension query based on the subquery
        query = query.where(col(ImageTable.sample_id).in_(label_filter))
    else:
        # If no labels specified, filter dimensions
        # for all samples in the collection
        query = query.where(SampleTable.collection_id == collection_id)

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
