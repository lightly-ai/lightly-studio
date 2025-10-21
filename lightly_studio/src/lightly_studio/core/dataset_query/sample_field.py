"""Fields for querying sample properties in the dataset query system."""

from __future__ import annotations

from sqlmodel import col

from lightly_studio.core.dataset_query.field import (
    DatetimeField,
    NumericalField,
    StringField,
)
from lightly_studio.core.dataset_query.tags_expression import TagsAccessor
from lightly_studio.models.sample import SampleTable


class SampleField:
    """Providing access to predefined sample fields for queries.

    This class provides static instances of different field types that can be
    used to build database queries on sample properties.
    """

    file_name = StringField(col(SampleTable.file_name))
    width = NumericalField(col(SampleTable.width))
    height = NumericalField(col(SampleTable.height))
    file_path_abs = StringField(col(SampleTable.file_path_abs))
    created_at = DatetimeField(col(SampleTable.created_at))
    tags = TagsAccessor()
