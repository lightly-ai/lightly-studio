"""Equal-width histogram bins shared by the histogram resolvers."""

from __future__ import annotations

import sqlalchemy
from sqlalchemy import Integer, cast, func


def bucket_expression(
    value: sqlalchemy.SQLColumnExpression[float] | sqlalchemy.SQLColumnExpression[int],
    min_value: float,
    max_value: float,
    bin_count: int,
) -> sqlalchemy.ColumnElement[int]:
    """Build the SQL expression for the bin index of ``value``.

    The expression uses dialect-independent functions (``floor``/``least``/``greatest``), so it
    works on DuckDB and PostgreSQL. Bin ``i`` covers the half-open interval
    ``[bin_edges[i], bin_edges[i + 1])``. A value equal to ``max_value`` goes to the last bin.

    Args:
        value: The SQL expression of the value to bin.
        min_value: The left edge of the first bin. Must be less than ``max_value``.
        max_value: The right edge of the last bin.
        bin_count: Number of equal-width bins.

    Returns:
        The bin index in ``[0, bin_count - 1]``.
    """
    width = (max_value - min_value) / bin_count
    raw_bucket = cast(func.floor((value - min_value) / width), Integer)
    return func.least(func.greatest(raw_bucket, 0), bin_count - 1)


def bin_edges(min_value: float, max_value: float, bin_count: int) -> list[float]:
    """Return the ``bin_count + 1`` edges of equal-width bins from min to max value."""
    edges = [min_value + (max_value - min_value) * i / bin_count for i in range(bin_count + 1)]
    # Guard against float drift so the last edge is exactly the max value.
    edges[-1] = max_value
    return edges
