"""Fields for querying sample properties in the dataset query system."""

from __future__ import annotations

from sqlmodel import col

from lightly_studio.core.dataset_query.field import (
    ComparableField,
    DatetimeField,
    NumericalField,
)
from lightly_studio.core.dataset_query.tags_expression import TagsAccessor
from lightly_studio.models.image import ImageTable


class ImageSampleField:
    """Providing access to predefined sample fields for queries.

    It is used for the `query.match(...)` and `query.order_by(...)` methods of the
    `DatasetQuery` class.

    ```python
    from lightly_studio.core.dataset_query import ImageSampleField, OrderByField

    query = dataset.query()
    query.match(ImageSampleField.tags.contains("cat"))
    query.order_by(OrderByField(ImageSampleField.file_path_abs))
    samples = query.to_list()
    ```
    """

    file_name = ComparableField(col(ImageTable.file_name))
    width = NumericalField(col(ImageTable.width))
    height = NumericalField(col(ImageTable.height))
    file_path_abs = ComparableField(col(ImageTable.file_path_abs))
    created_at = DatetimeField(col(ImageTable.created_at))
    tags = TagsAccessor()
