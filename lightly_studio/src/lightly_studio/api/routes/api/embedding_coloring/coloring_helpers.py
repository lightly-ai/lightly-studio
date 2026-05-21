"""Generic helpers for assigning per-sample color categories."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar
from uuid import UUID

T = TypeVar("T")
T_contra = TypeVar("T_contra", contravariant=True)


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

        Args:
            values: Values to assign color categories to, in the desired order.
                Values must be unique.
            start_cat: First category ID to assign. Defaults to 2, reserving
                0 for filtered-out samples and 1 for unassigned samples.
            format_fn: Function to produce a legend label from a value.
                Defaults to ``str``.

        Returns:
            A DiscreteColorScale with one category per value.
        """
        value_list = list(values)
        assert len(set(value_list)) == len(value_list), "Color legend values must be unique"

        lookup: dict[T, int] = {}
        legend: dict[int, str] = {}
        for i, value in enumerate(value_list):
            cat = start_cat + i
            lookup[value] = cat
            legend[cat] = format_fn(value)
        return cls(_lookup=lookup, legend=legend)

    @classmethod
    def from_lookup(
        cls,
        lookup: dict[T, int],
        legend: dict[int, str],
    ) -> DiscreteColorScale[T]:
        """Build a DiscreteColorScale from a pre-computed lookup and legend.

        Use this when multiple values map to the same category (e.g. buckets),
        which ``from_values`` cannot express.

        Args:
            lookup: Mapping from value to color category integer.
            legend: Mapping from color category integer to a human-readable label.

        Returns:
            A DiscreteColorScale backed by the provided lookup and legend.
        """
        return cls(_lookup=lookup, legend=legend)


def assign_color_categories(
    sample_ids: Sequence[UUID],
    fulfils_filter: Sequence[int],
    sample_to_value: Mapping[UUID, T],
    scale: ColorScale[T],
) -> tuple[list[int], dict[int, str]]:
    """Return color categories and a legend for the given samples.

    Args:
        sample_ids: Sample IDs.
        fulfils_filter: Binary indicator per sample. 0 means filtered out.
        sample_to_value: Mapping from sample ID to a value.
        scale: Color scale used to map values to categories.

    Returns:
        A tuple of `(color_categories, legend)`. Category 0 means filtered
        out and 1 means unassigned (missing or unmapped value).
    """
    color_categories: list[int] = []
    for i, sid in enumerate(sample_ids):
        if fulfils_filter[i] == 0:
            cat = 0
        elif sid in sample_to_value:
            mapped = scale.value_to_category(sample_to_value[sid])
            cat = mapped if mapped is not None else 1
        else:
            cat = 1
        color_categories.append(cat)

    legend = {0: "Filtered out", 1: "Unassigned", **scale.legend}
    return color_categories, legend


def first_match_per_sample(
    sample_to_candidates: Mapping[UUID, Iterable[T]],
    priority_order: Sequence[T],
) -> dict[UUID, T]:
    """Map each sample to the first matching value from a priority-ordered list.

    Samples with no match are omitted from the result.

    Args:
        sample_to_candidates: Mapping from sample ID to the set (or any
            iterable) of candidate values the sample carries.
        priority_order: Values in priority order — the first match wins.

    Returns:
        A mapping from sample ID to the winning value.
    """
    result: dict[UUID, T] = {}
    for sid, candidates in sample_to_candidates.items():
        candidate_set = candidates if isinstance(candidates, set) else set(candidates)
        for value in priority_order:
            if value in candidate_set:
                result[sid] = value
                break
    return result
