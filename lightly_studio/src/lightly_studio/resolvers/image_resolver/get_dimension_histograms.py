"""Implementation of get_dimension_histograms function for images."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal
from uuid import UUID

from sqlalchemy.orm import Mapped
from sqlmodel import Session, col, func, select

from lightly_studio.models.image import ImageTable
from lightly_studio.models.metadata import HistogramView
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import histogram_bins
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.type_definitions import QueryType

ImageDimension = Literal["width", "height"]
"""An image field with a histogram."""

IMAGE_DIMENSIONS: tuple[ImageDimension, ...] = ("width", "height")

# Number of bins used for image dimension histograms.
_HISTOGRAM_BIN_COUNT = 20

_COLUMNS: dict[ImageDimension, Mapped[int]] = {
    "width": col(ImageTable.width),
    "height": col(ImageTable.height),
}


def get_dimension_histograms(
    session: Session,
    collection_id: UUID,
    filters: ImageFilter | None = None,
    bin_count: int = _HISTOGRAM_BIN_COUNT,
    fields: Sequence[ImageDimension] | None = None,
) -> dict[str, HistogramView]:
    """Compute value-distribution histograms of the image width and height.

    The bin edges span the unfiltered value range of each field, so the chart axis stays stable
    while the filters change. The histogram of a field ignores the filter of that field and
    applies all other filters (faceted-search behavior).

    Args:
        session: The database session.
        collection_id: The collection's UUID.
        filters: Optional image filters restricting which images are counted.
        bin_count: Number of equal-width bins per histogram.
        fields: Optional fields to include. All fields are included when absent.

    Returns:
        Mapping of field name to its histogram. Empty when the collection has no images.
    """
    histograms: dict[str, HistogramView] = {}
    for field in IMAGE_DIMENSIONS:
        if fields is not None and field not in fields:
            continue
        column = _COLUMNS[field]
        min_value, max_value = session.execute(
            _restrict(
                query=select(func.min(column), func.max(column)).select_from(ImageTable),
                collection_id=collection_id,
                filters=None,
            )
        ).one()
        if min_value is None or max_value is None:
            continue
        histograms[field] = _compute_histogram(
            session=session,
            collection_id=collection_id,
            column=column,
            min_value=float(min_value),
            max_value=float(max_value),
            filters=filters.model_copy(update={field: None}) if filters is not None else None,
            bin_count=bin_count,
        )
    return histograms


def _compute_histogram(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    column: Mapped[int],
    min_value: float,
    max_value: float,
    filters: ImageFilter | None,
    bin_count: int,
) -> HistogramView:
    """Compute the histogram of one image column under the given filters.

    When all values are equal, the range is degenerate and a single bin holds every value.
    """
    if max_value == min_value:
        count_query = _restrict(
            query=select(func.count()).select_from(ImageTable),
            collection_id=collection_id,
            filters=filters,
        )
        return HistogramView(
            bin_edges=[min_value, max_value], counts=[int(session.exec(count_query).one())]
        )

    bucket_expr = histogram_bins.bucket_expression(
        value=column, min_value=min_value, max_value=max_value, bin_count=bin_count
    )
    query = _restrict(
        query=select(bucket_expr, func.count()).select_from(ImageTable),
        collection_id=collection_id,
        filters=filters,
    ).group_by(bucket_expr)
    counts_by_bucket = {int(bucket): int(count) for bucket, count in session.exec(query).all()}
    return HistogramView(
        bin_edges=histogram_bins.bin_edges(
            min_value=min_value, max_value=max_value, bin_count=bin_count
        ),
        counts=[counts_by_bucket.get(i, 0) for i in range(bin_count)],
    )


def _restrict(query: QueryType, collection_id: UUID, filters: ImageFilter | None) -> QueryType:
    """Restrict a query on ``ImageTable`` to the images of a collection that match ``filters``."""
    query = query.join(ImageTable.sample).where(SampleTable.collection_id == collection_id)
    if filters is None:
        return query
    return query.where(
        col(ImageTable.sample_id).in_(filters.build_sample_ids_query(collection_id=collection_id))
    )
