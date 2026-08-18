"""Build the base annotation count query grouped by sample tag and label."""

from __future__ import annotations

from typing import Optional, cast
from uuid import UUID

from sqlmodel import col, select
from sqlmodel.sql.expression import Select

from lightly_studio.database import db_array
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable, SampleTagLinkTable
from lightly_studio.resolvers.image_resolver.annotation_count_types import AnnotationCountMode

from .build_count_expression import build_count_expression


def build_grouped_count_query(
    collection_id: UUID,
    sample_tag_ids: list[UUID],
    count_mode: AnnotationCountMode,
) -> Select[tuple[UUID | None, str, int]]:
    """Build the join chain for annotation counts grouped by tag and label."""
    return cast(
        Select[tuple[Optional[UUID], str, int]],
        select(
            SampleTagLinkTable.tag_id,
            AnnotationLabelTable.annotation_label_name,
            build_count_expression(count_mode).label("count"),
        )
        .join(
            AnnotationBaseTable,
            col(AnnotationBaseTable.annotation_label_id)
            == col(AnnotationLabelTable.annotation_label_id),
        )
        .join(
            ImageTable,
            col(ImageTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        )
        .join(SampleTable, col(SampleTable.sample_id) == col(ImageTable.sample_id))
        .join(
            SampleTagLinkTable,
            col(SampleTagLinkTable.sample_id) == col(SampleTable.sample_id),
        )
        .where(
            col(SampleTable.collection_id) == collection_id,
            db_array.in_array(column=col(SampleTagLinkTable.tag_id), values=sample_tag_ids),
        ),
    )  # cast: tag_id is UUID | None per model but always non-null in practice
