"""Restrict an annotation query to specific source collections."""

from __future__ import annotations

from typing import TypeVar
from uuid import UUID

from sqlalchemy.orm import aliased
from sqlmodel import col
from sqlmodel.sql.expression import Select

from lightly_studio.database import db_array
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.sample import SampleTable

_SelectRow = TypeVar("_SelectRow")


def restrict_to_annotation_sources(
    query: Select[_SelectRow],
    annotation_collection_ids: list[UUID],
) -> Select[_SelectRow]:
    """Restrict the counted annotations to the given source collections.

    The annotation's own sample (aliased to avoid clashing with the image sample
    joined by the caller) carries its collection id.
    """
    annotation_sample = aliased(SampleTable)
    return query.join(
        annotation_sample,
        col(annotation_sample.sample_id) == col(AnnotationBaseTable.sample_id),
    ).where(
        db_array.in_array(
            column=col(annotation_sample.collection_id),
            values=annotation_collection_ids,
        )
    )
