"""Dataset query utilities for filtering, ordering, and slicing samples."""

from __future__ import annotations

from typing import Generic, Iterator, Type, cast

from sqlmodel import Session, select
from sqlmodel.sql.expression import SelectOfScalar
from typing_extensions import Self, TypeVar

from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.core.dataset_query.order_by import OrderByExpression, OrderByField
from lightly_studio.core.image_sample import ImageSample
from lightly_studio.core.sample import Sample
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoTable
from lightly_studio.resolvers import tag_resolver
from lightly_studio.selection.select import Selection

_SliceType = slice  # to avoid shadowing built-in slice in type annotations


T = TypeVar("T", default=ImageSample, bound=Sample)
Table = TypeVar("Table", default=ImageTable)


class DatasetQuery(Generic[T]):
    """Class for executing a query on a dataset.

    # Filtering, ordering, and slicing samples in a dataset
    Allows filtering, ordering, and slicing of samples in a dataset.
    This class can be accessed via calling `.query()` on a Dataset instance.
    ```python
    dataset : Dataset = ...
    query = dataset.query()
    ```
    The `match()`, `order_by()`, and `slice()` methods can be chained in this order.
    You can also access the methods directly on the Dataset instance:
    ```python
    dataset.match(...) # shorthand for dataset.query().match(...)
    ```

    The object is converted to a SQL query that is lazily evaluated when iterating over
    it or converting it to a list.

    ## match() - Filtering samples
    Filtering is done via the `match()` method.
    ```python
    from lightly_studio.core.dataset_query import ImageSampleField

    query_1 = dataset.query().match(ImageSampleField.width > 100)
    query_2 = dataset.query().match(ImageSampleField.tags.contains('cat'))
    ```
    AND and OR operators are available for combining multiple conditions.
    ```python
    from lightly_studio.core.dataset_query import ImageSampleField, AND, OR

    query = dataset.query().match(
        AND(
            ImageSampleField.height < 200,
            OR(
                ImageSampleField.file_name == 'image.png',
                ImageSampleField.file_name == 'image2.png',
            )
        )
    )
    ```

    ## order_by() - Ordering samples
    The results can be ordered by using `order_by()`. For tie-breaking, multiple fields
    can be provided. The first field has the highest priority. The default is
    ascending order. To order in descending order, use `OrderByField(...).desc()`.
    ```python
    from lightly_studio.core.dataset_query import OrderByField, ImageSampleField
    query = query.order_by(
        OrderByField(ImageSampleField.width),
        OrderByField(ImageSampleField.file_name).desc()
    )
    ```

    ## slice() - Slicing samples
    Slicing can be applied via `slice()` or bracket notation.
    ```python
    query = query.slice(offset=10, limit=20)
    query = query[10:30]  # equivalent to slice(offset=10, limit=20)
    ```

    # Usage of the filtered, ordered and sliced query

    ## Iterating and converting to list
    Finally, the query can be executed by iterating over it or converting to a list.
    ```python
    for sample in query:
        print(sample.file_name)
    samples = query.to_list()
    ```
    The samples returned are instances of the `Sample` class. They are writable, and
    changes to them will be persisted to the database.

    ## Adding tags to matching samples
    The filtered set can also be used to add a tag to all matching samples.
    ```python
    query.add_tag('my_tag')
    ```

    ## Selecting a subset of samples using smart selection
    A Selection interface can be created from the current query results. It will only
    select the samples matching the current query at the time of calling selection().
    ```python
    # Choosing 100 diverse samples from the 'cat' tag.
    # Save them under the tag name "diverse_cats".
    selection = dataset.query().match(
        ImageSampleField.tags.contains('cat')
    ).selection()
    selection.diverse(100, "diverse_cats")
    ```

    ## Exporting the query results
    An export interface can be created from the current query results.
    ```python
    query = dataset.query().match(...)
    export = dataset.export(query)
    export.to_coco_object_detections('/path/to/coco.json')
    ```
    """

    def __init__(
        self, dataset: CollectionTable, session: Session, sample_class: type[T] | None = None
    ) -> None:
        """Initialize with dataset and database session.

        Args:
            dataset: The dataset to query.
            session: Database session for executing queries.
            sample_class: The class of type `T`.
        """
        # TODO(lukas 12/2025): it would be great to assert that sample_class is the same as
        # self.dataset.sample_type.
        self.dataset = dataset
        self.session = session
        self.match_expression: MatchExpression | None = None
        self.order_by_expressions: list[OrderByExpression] | None = None
        self._slice: _SliceType | None = None
        if sample_class is None:
            # TODO(lukas 12/2025): Remove once we introduce ImageDatasetQuery. Right now
            # T=ImageSample is the default, so this is fine.
            self._sample_class = cast(Type[T], ImageSample)
        else:
            self._sample_class = sample_class

    def match(self, match_expression: MatchExpression) -> Self:
        """Store a field condition for filtering.

        Args:
            match_expression: Defines the filter.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If match() has already been called on this instance.
        """
        if self.match_expression is not None:
            raise ValueError("match() can only be called once per DatasetQuery instance")

        self.match_expression = match_expression
        return self

    def order_by(self, *order_by: OrderByExpression) -> Self:
        """Store ordering expressions.

        Args:
            order_by: One or more ordering expressions. They are applied in order.
                E.g. first ordering by sample width and then by sample file_name will
                only order the samples with the same sample width by file_name.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If order_by() has already been called on this instance.
        """
        if self.order_by_expressions:
            raise ValueError("order_by() can only be called once per DatasetQuery instance")

        self.order_by_expressions = list(order_by)
        return self

    def slice(self, offset: int = 0, limit: int | None = None) -> Self:
        """Apply offset and limit to results.

        Args:
            offset: Number of items to skip from beginning (default: 0).
            limit: Maximum number of items to return (None = no limit).

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If slice() has already been called on this instance.
        """
        if self._slice is not None:
            raise ValueError("slice() can only be called once per DatasetQuery instance")

        # Convert to slice object for internal consistency
        stop = None if limit is None else offset + limit
        self._slice = _SliceType(offset, stop)
        return self

    def __getitem__(self, key: _SliceType) -> Self:
        """Enable bracket notation for slicing.

        Args:
            key: A slice object (e.g., [10:20], [:50], [100:]).

        Returns:
            Self with slice applied.

        Raises:
            TypeError: If key is not a slice object.
            ValueError: If slice contains unsupported features or conflicts with existing slice.
        """
        if not isinstance(key, _SliceType):
            raise TypeError(
                "DatasetQuery only supports slice notation, not integer indexing. "
                "Use execute() to get results as a list for element access."
            )

        # Validate unsupported features
        if key.step is not None:
            raise ValueError("Strides are not supported. Use simple slices like [start:stop].")

        if (key.start is not None and key.start < 0) or (key.stop is not None and key.stop < 0):
            raise ValueError("Negative indices are not supported. Use positive indices only.")

        # Check for conflicts with existing slice
        if self._slice is not None:
            raise ValueError("Cannot use bracket notation after slice() has been called.")

        # Set slice and return self
        self._slice = key
        return self

    def __iter__(self) -> Iterator[T]:
        """Iterate over the query results.

        Returns:
            Iterator of Sample objects from the database.
        """
        if self.dataset.sample_type == SampleType.IMAGE:
            image_query: SelectOfScalar[ImageTable] = (
                select(ImageTable)
                .join(ImageTable.sample)
                .where(SampleTable.collection_id == self.dataset.collection_id)
            )
            image_query = self._compose_query(image_query)
            for image_table in self.session.exec(image_query):
                # Calling the constructor of `ImageSample`
                yield self._sample_class(image_table)  # type: ignore[arg-type]
        elif self.dataset.sample_type == SampleType.VIDEO:
            video_query: SelectOfScalar[VideoTable] = (
                select(VideoTable)
                .join(VideoTable.sample)
                .where(SampleTable.collection_id == self.dataset.collection_id)
            )
            video_query = self._compose_query(video_query)
            for video_table in self.session.exec(video_query):
                # Calling the constructor of `VideoSample`
                yield self._sample_class(video_table)  # type: ignore[arg-type]
        else:
            raise NotImplementedError(
                f"Iter is not implemented for sample type {self.dataset.sample_type}"
            )

    def _compose_query(self, query: SelectOfScalar[Table]) -> SelectOfScalar[Table]:
        """Applies match expressions, slicing, etc., to the query."""
        # Apply filter if present
        if self.match_expression:
            query = query.where(self.match_expression.get())

        # Apply ordering
        if self.order_by_expressions:
            for order_by in self.order_by_expressions:
                query = order_by.apply(query)
        elif self.dataset.sample_type == SampleType.IMAGE:
            # TODO(lukas 1/2026): provide default order for other sample types
            # Order by ImageSampleField.created_at by default.
            default_order_by = OrderByField(ImageSampleField.created_at)
            query = default_order_by.apply(query)

        # Apply slicing if present
        if self._slice is not None:
            start = self._slice.start or 0
            query = query.offset(start)
            if self._slice.stop is not None:
                limit = max(self._slice.stop - start, 0)
                query = query.limit(limit)
        return query

    def to_list(self) -> list[T]:
        """Execute the query and return the results as a list.

        Returns:
            List of Sample objects from the database.
        """
        return list(self)

    def add_tag(self, tag_name: str) -> None:
        """Add a tag to all samples returned by this query.

        First, creates the tag if it doesn't exist. Then applies the tag to all samples
        that match the current query filters. Samples already having that tag are unchanged,
        as the database prevents duplicates.

        Args:
            tag_name: Name of the tag to add to matching samples.
        """
        # Get or create the tag
        tag = tag_resolver.get_or_create_sample_tag_by_name(
            session=self.session, collection_id=self.dataset.collection_id, tag_name=tag_name
        )

        # Execute query to get matching samples
        samples = self.to_list()
        sample_ids = [sample.sample_id for sample in samples]

        # Use resolver to bulk assign tag (handles validation and edge cases)
        tag_resolver.add_sample_ids_to_tag_id(
            session=self.session, tag_id=tag.tag_id, sample_ids=sample_ids
        )

    def selection(self) -> Selection:
        """Selection interface for this query.

        The returned Selection snapshots the current query results immediately.
        Mutating the query after calling this method will therefore not affect
        the samples used by that Selection instance.

        Returns:
            Selection interface operating on the current query result snapshot.
        """
        input_sample_ids = (sample.sample_id for sample in self)
        return Selection(
            dataset_id=self.dataset.collection_id,
            session=self.session,
            input_sample_ids=input_sample_ids,
        )
