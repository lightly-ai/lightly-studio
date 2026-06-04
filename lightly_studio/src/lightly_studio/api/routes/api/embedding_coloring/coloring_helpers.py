"""Generic helpers for assigning per-sample color categories."""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar
from uuid import UUID

T = TypeVar("T")
T_contra = TypeVar("T_contra", contravariant=True)

# The plotting library renders at most this many legend slots, indexed [0, MAX_LEGEND_SLOTS).
MAX_LEGEND_SLOTS = 256
# Number of category names listed inside an "Other" bucket label before truncating with an ellipsis.
_MAX_OTHER_NAMES = 5


class ColorScale(Protocol[T_contra]):
    """Protocol for mapping values to color categories.

    Attributes:
        legend: Mapping from color category integer to a human-readable label.
    """

    @property
    def legend(self) -> dict[int, str]:
        """Mapping from color category integer to a human-readable label."""
        ...

    def value_to_category(self, value: T_contra) -> int | None:
        """Return the color category for a value, or None if unmapped."""
        ...


@dataclass(frozen=True)
class DiscreteColorScale(Generic[T]):
    """ColorScale implementation for a finite set of discrete values.

    Attributes:
        legend: Mapping from color category integer to a human-readable label.
    """

    _lookup: dict[T, int]
    legend: dict[int, str]

    def value_to_category(self, value: T) -> int | None:
        """Return the color category for a value, or None if unmapped."""
        return self._lookup.get(value)

    @classmethod
    def from_values(
        cls,
        values: Iterable[T],
        start_cat: int = 2,
        format_fn: Callable[[T], str] = str,
    ) -> DiscreteColorScale[T]:
        """Build a DiscreteColorScale by assigning a category to each value.

        Values are consumed in iteration order — the caller is responsible for
        providing them in the desired sequence (e.g. sorted alphabetically or
        in priority order).

        The plotting library can render at most ``MAX_LEGEND_SLOTS`` legend
        slots. Categories occupy the slots ``[start_cat, MAX_LEGEND_SLOTS)``;
        the slots below ``start_cat`` are reserved (e.g. filtered-out and
        unassigned samples). When the values fit in those slots, each value gets
        its own category. Otherwise the values that fit are listed individually
        and every remaining value is grouped into a trailing "Other" category in
        the final slot.

        Args:
            values: Values to assign color categories to, in the desired order.
                Values must be unique.
            start_cat: First category ID to assign. Defaults to 2, reserving
                0 for filtered-out samples and 1 for unassigned samples.
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
    def from_integers(
        cls,
        values: Iterable[int],
        start_cat: int = 2,
        max_categories: int = 50,
    ) -> DiscreteColorScale[int]:
        """Build a color scale for integer values.

        When the number of unique values is at most ``max_categories``, each
        unique value gets its own category. Otherwise the range [min, max] is
        split into at most ``max_categories`` equal-width buckets and each value
        is mapped to the bucket that contains it.

        In both cases categories are ordered numerically (smallest value first).

        Args:
            values: Integer values to build the scale from. Need not be unique.
            start_cat: First category ID to assign. Defaults to 2, reserving
                0 for filtered-out samples and 1 for unassigned samples.
            max_categories: Maximum number of distinct color categories before
                bucketing is applied. Defaults to 50.

        Returns:
            A DiscreteColorScale mapping each integer to a color category.
        """
        unique_values = sorted(set(values))

        if len(unique_values) <= max_categories:
            return DiscreteColorScale.from_values(values=unique_values, start_cat=start_cat)

        min_val = unique_values[0]
        max_val = unique_values[-1]
        value_range = max_val - min_val
        raw_width = value_range / max_categories
        magnitude = 10 ** math.floor(math.log10(raw_width)) if raw_width >= 1 else 1
        bucket_width = math.ceil(raw_width / magnitude) * magnitude

        num_buckets = math.ceil((value_range + 1) / bucket_width)

        def _bucket_idx(value: int) -> int:
            return min((value - min_val) // bucket_width, num_buckets - 1)

        def _label(bucket_start: int) -> str:
            if bucket_width == 1:
                return str(bucket_start)
            return f"{bucket_start}-{bucket_start + bucket_width - 1}"

        legend: dict[int, str] = {
            start_cat + i: _label(min_val + i * bucket_width) for i in range(num_buckets)
        }
        lookup: dict[int, int] = {v: start_cat + _bucket_idx(v) for v in unique_values}

        return DiscreteColorScale[int](_lookup=lookup, legend=legend)


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


def _format_other_label(values: Sequence[T], format_fn: Callable[[T], str]) -> str:
    """Build the legend label for an "Other" bucket, e.g. ``Other (class1, class2, …)``."""
    names = [format_fn(value) for value in values[:_MAX_OTHER_NAMES]]
    if len(values) > _MAX_OTHER_NAMES:
        names.append("…")
    return f"Other ({', '.join(names)})"
