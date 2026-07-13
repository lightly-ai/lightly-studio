"""Generic helpers for assigning per-sample color categories."""

from __future__ import annotations

import bisect
import math
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Generic, Protocol, TypeVar
from uuid import UUID

T = TypeVar("T")
T_contra = TypeVar("T_contra", contravariant=True)

# The plotting library renders at most this many legend slots, indexed [0, MAX_LEGEND_SLOTS).
MAX_LEGEND_SLOTS = 256
# First slot available for colored categories. Slots below it are reserved for the
# frontend's non-colored categories (0 hidden, 1 filtered-out, 2 unassigned).
FIRST_COLORED_CATEGORY = 3
# Number of category names listed inside an "Other" bucket label before truncating with an ellipsis.
MAX_OTHER_NAMES = 5
# Target number of quantile bins for numeric (ordered) coloring.
DEFAULT_NUM_QUANTILE_BINS = 8


@dataclass(frozen=True)
class ColorData:
    """Per-sample color categories plus the legend describing them.

    Attributes:
        color_categories: One list per sample, holding that sample's color
            categories sorted ascending.
        color_legend: Mapping from color category integer to a human-readable label.
        ordered: Whether the categories form an ordered sequence (e.g. numeric
            quantile bins) that the frontend should render as a sequential color
            ramp rather than an unordered categorical palette.
    """

    color_categories: list[list[int]]
    color_legend: dict[int, str]
    ordered: bool = False


class ColorScale(Protocol[T_contra]):
    """Protocol for mapping values to color categories.

    Attributes:
        legend: Mapping from color category integer to a human-readable label.
    """

    @property
    def legend(self) -> dict[int, str]:
        """Mapping from color category integer to a human-readable label."""
        ...

    @property
    def ordered(self) -> bool:
        """Whether the categories form an ordered sequence (e.g. numeric bins)."""
        ...

    def value_to_category(self, value: T_contra) -> int | None:
        """Return the color category for a value, or None if unmapped."""
        ...


@dataclass(frozen=True)
class DiscreteColorScale(Generic[T]):
    """ColorScale implementation for a finite set of discrete values.

    Attributes:
        legend: Mapping from color category integer to a human-readable label.
        ordered: Whether the categories form an ordered sequence (e.g. numeric
            quantile bins) rather than an unordered categorical set.
    """

    _lookup: dict[T, int]
    legend: dict[int, str]
    ordered: bool = field(default=False)

    def value_to_category(self, value: T) -> int | None:
        """Return the color category for a value, or None if unmapped."""
        return self._lookup.get(value)

    @classmethod
    def from_values(
        cls,
        values: Iterable[T],
        start_cat: int = FIRST_COLORED_CATEGORY,
        format_fn: Callable[[T], str] = str,
    ) -> DiscreteColorScale[T]:
        """Build a DiscreteColorScale by assigning a category to each value.

        Values are consumed in iteration order — the caller is responsible for
        providing them in the desired sequence (e.g. sorted alphabetically or
        in priority order).

        The plotting library can render at most ``MAX_LEGEND_SLOTS`` legend
        slots. Categories occupy the slots ``[start_cat, MAX_LEGEND_SLOTS)``;
        the slots below ``start_cat`` are reserved (e.g. hidden, filtered-out
        and unassigned samples). When the values fit in those slots, each value gets
        its own category. Otherwise the values that fit are listed individually
        and every remaining value is grouped into a trailing "Other" category in
        the final slot.

        Args:
            values: Values to assign color categories to, in the desired order.
                Values must be unique.
            start_cat: First category ID to assign. Defaults to 3, reserving
                0 for hidden samples, 1 for filtered-out samples and 2 for
                unassigned samples.
            format_fn: Function to produce a legend label from a value.
                Defaults to ``str``.

        Returns:
            A DiscreteColorScale with one category per value, or — when the
            values exceed the available slots — one category per value that fits
            plus a final "Other" category grouping the remainder.
        """
        value_list = list(values)
        assert len(set(value_list)) == len(value_list), "Color legend values must be unique"

        # Slots [start_cat, MAX_LEGEND_SLOTS) are available for categories.
        max_individual = MAX_LEGEND_SLOTS - start_cat

        lookup: dict[T, int] = {}
        legend: dict[int, str] = {}

        # When values overflow the slots, reserve the final slot for an "Other"
        # bucket; otherwise every value gets its own slot.
        fits = len(value_list) <= max_individual
        individual = value_list if fits else value_list[: max_individual - 1]
        for i, value in enumerate(individual):
            cat = start_cat + i
            lookup[value] = cat
            legend[cat] = format_fn(value)

        if not fits:
            other = value_list[max_individual - 1 :]
            other_cat = start_cat + max_individual - 1
            for value in other:
                lookup[value] = other_cat
            legend[other_cat] = _format_other_label(other, format_fn)

        return cls(_lookup=lookup, legend=legend)

    @classmethod
    def from_quantiles(
        cls,
        values: Iterable[float],
        start_cat: int = FIRST_COLORED_CATEGORY,
        num_bins: int = DEFAULT_NUM_QUANTILE_BINS,
    ) -> DiscreteColorScale[float]:
        """Build an ordered color scale for numeric values using quantile bins.

        Bin edges are chosen so each bin holds roughly the same number of samples
        (equal-frequency binning), which makes color contrast reflect the actual
        distribution rather than the raw value range. Bins are labeled with their
        value range (e.g. ``0.1-0.42``) and ordered from lowest to highest, so the
        returned scale is marked ``ordered`` for a sequential color ramp.

        When there are at most ``num_bins`` distinct values, each distinct value
        gets its own category labeled with the value itself, keeping small-range
        integer fields readable.

        Args:
            values: Numeric values to build the scale from. Need not be unique.
            start_cat: First category ID to assign. Defaults to 3, reserving
                0 for hidden samples, 1 for filtered-out samples and 2 for
                unassigned samples.
            num_bins: Target number of quantile bins. Fewer bins result when the
                data has fewer distinct quantile edges (e.g. many repeated values).

        Returns:
            An ordered DiscreteColorScale mapping each value to its bin's category.
        """
        # Non-finite values (NaN/inf) cannot be binned or labeled; drop them so the
        # affected samples fall through to the "missing value" (gray) path.
        value_list = sorted(f for v in values if math.isfinite(f := float(v)))
        if not value_list:
            return DiscreteColorScale[float](_lookup={}, legend={}, ordered=True)

        unique_values = sorted(set(value_list))
        if len(unique_values) <= num_bins:
            legend = {start_cat + i: _format_number(v) for i, v in enumerate(unique_values)}
            lookup: dict[float, int] = {v: start_cat + i for i, v in enumerate(unique_values)}
            return DiscreteColorScale[float](_lookup=lookup, legend=legend, ordered=True)

        edges = _quantile_bin_edges(sorted_values=value_list, num_bins=num_bins)
        # Interior edges separate adjacent bins; a value falls into the bin whose
        # upper edge is the first strictly greater than it.
        interior_edges = edges[1:-1]
        num_actual_bins = len(edges) - 1

        legend = {
            start_cat + i: _bin_label(low=edges[i], high=edges[i + 1])
            for i in range(num_actual_bins)
        }
        lookup = {
            value: start_cat + bisect.bisect_right(interior_edges, value)
            for value in unique_values
        }
        return DiscreteColorScale[float](_lookup=lookup, legend=legend, ordered=True)


def assign_color_categories(
    sample_ids: Sequence[UUID],
    sample_to_values: Mapping[UUID, Iterable[T]],
    scale: ColorScale[T],
) -> tuple[list[list[int]], dict[int, str]]:
    """Return per-sample color category list and a legend for the given samples.

    Each sample maps to the color categories of its values, sorted by color
    category. A sample with no value (or no value that maps to a category) maps
    to an empty list.

    Args:
        sample_ids: Sample IDs.
        sample_to_values: Mapping from sample ID to the values it carries.
        scale: Color scale used to map values to categories.

    Returns:
        A tuple of `(color_categories, legend)`. Each per-sample list holds the
        sample's color categories, sorted ascending.
    """
    color_categories: list[list[int]] = []
    for sid in sample_ids:
        values = sample_to_values.get(sid, ())
        categories = [scale.value_to_category(value) for value in values]
        categories_not_none = [c for c in categories if c is not None]
        color_categories.append(sorted(categories_not_none))

    return color_categories, scale.legend


def order_values_by_frequency(
    sample_to_values: Mapping[UUID, Iterable[T]],
    matching_sample_ids: set[UUID] | None,
    format_fn: Callable[[T], str] = str,
) -> list[T]:
    """Distinct values among matching samples, ordered by descending frequency.

    Counting only the samples in ``matching_sample_ids`` (all samples when it is
    ``None``) makes the result *filter-aware*. When the values are later split
    into a fixed number of legend slots, this ordering ensures the values most
    common among the matching samples each get a dedicated category, while the
    less common ones are merged into a single "Other" category. Values that never
    occur in a matching sample are omitted entirely, which hides categories with
    zero samples after filtering.

    Args:
        sample_to_values: Mapping from sample ID to the values it carries.
        matching_sample_ids: Sample IDs to count. ``None`` counts every sample
            in ``sample_to_values``.
        format_fn: Function producing the label used to break frequency ties,
            keeping the ordering deterministic. Defaults to ``str``.

    Returns:
        Distinct values sorted by ``(-count, format_fn(value))``.
    """
    counts: Counter[T] = Counter()
    for sample_id, values in sample_to_values.items():
        if matching_sample_ids is not None and sample_id not in matching_sample_ids:
            continue
        counts.update(set(values))

    return sorted(counts, key=lambda value: (-counts[value], format_fn(value)))


def _quantile_bin_edges(sorted_values: list[float], num_bins: int) -> list[float]:
    """Return ``num_bins`` quantile bin edges (actual data values) for sorted input.

    Edges are the values at the nearest-rank quantile positions, so each of the
    ``num_bins`` bins holds roughly the same number of samples. Consecutive equal
    edges are collapsed, which yields fewer bins when the data is concentrated. The
    result always contains at least two edges (a single degenerate bin).
    """
    n = len(sorted_values)
    raw_edges = [sorted_values[round(i / num_bins * (n - 1))] for i in range(num_bins + 1)]

    edges = [raw_edges[0]]
    for edge in raw_edges[1:]:
        if edge != edges[-1]:
            edges.append(edge)

    if len(edges) == 1:
        edges.append(edges[0])
    return edges


def _bin_label(low: float, high: float) -> str:
    """Legend label for a quantile bin, e.g. ``0.1-0.42`` (or a single value)."""
    if low == high:
        return _format_number(low)
    return f"{_format_number(low)}-{_format_number(high)}"


def _format_number(value: float) -> str:
    """Format a numeric value compactly, dropping the decimals of whole numbers."""
    if value == int(value):
        return str(int(value))
    return f"{value:g}"


def _format_other_label(values: Sequence[T], format_fn: Callable[[T], str]) -> str:
    """Build the legend label for an "Other" bucket, e.g. ``Other (class1, class2, …)``."""
    names = [format_fn(value) for value in values[:MAX_OTHER_NAMES]]
    if len(values) > MAX_OTHER_NAMES:
        names.append("…")
    return f"Other ({', '.join(names)})"
