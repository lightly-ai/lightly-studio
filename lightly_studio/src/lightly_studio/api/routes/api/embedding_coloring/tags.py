"""Tag-based coloring helpers for 2D embedding plots."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session

from lightly_studio.api.routes.api.embedding_coloring.coloring_helpers import DiscreteColorScale
from lightly_studio.resolvers import tag_resolver
from lightly_studio.resolvers.tag_resolver import iter_sample_memberships


@dataclass(frozen=True)
class _GroupedMemberships:
    """Tag memberships and their frequencies within the active filter.

    Attributes:
        samples_by_tag: All sample IDs grouped by tag ID, stored as strings.
        matching_counts: Number of filter-matching samples for each tag ID.
    """

    samples_by_tag: dict[str, list[str]]
    matching_counts: Counter[str]


def build_tag_color_maps(
    session: Session,
    tag_ids: list[UUID],
    sample_ids: list[UUID],
    matching_sample_ids: set[UUID] | None,
) -> tuple[list[list[int]], dict[int, str]]:
    """Build color categories and a legend for tag-based sample coloring.

    When more tags are selected than fit in the legend, the tags carried by the
    most filter-matching samples each get a dedicated color category and the rest
    are merged into a single "Other" category. Tags with no matching sample are
    omitted from the legend entirely.

    Args:
        session: Database session.
        tag_ids: Tag IDs to color by.
        sample_ids: Sample IDs in the order for which to build color categories.
        matching_sample_ids: Sample IDs matching the active filter. Tags are
            prioritized by their frequency among these samples. ``None`` counts
            all samples.

    Returns:
        A tuple of `(color_categories, color_legend)` for the provided samples. The
        length of `color_categories` is the number of samples; each entry is the
        list of that sample's color categories, sorted ascending. The `color_legend`
        is a mapping from color ID to a human-readable string.
    """
    names = {
        str(tag_id): name
        for tag_id, name in tag_resolver.get_names_by_ids(session=session, tag_ids=tag_ids).items()
    }
    memberships = _group_memberships(
        session=session, tag_ids=tag_ids, matching_sample_ids=matching_sample_ids
    )
    ordered_tag_ids = sorted(
        memberships.matching_counts,
        key=lambda tid: (-memberships.matching_counts[tid], names.get(tid, tid)),
    )
    scale = DiscreteColorScale.from_values(
        values=ordered_tag_ids,
        format_fn=lambda tid: names.get(tid, tid),
    )
    return _assign_categories(
        sample_ids=sample_ids,
        samples_by_tag=memberships.samples_by_tag,
        ordered_tag_ids=ordered_tag_ids,
        scale=scale,
    ), scale.legend


def _assign_categories(
    sample_ids: list[UUID],
    samples_by_tag: dict[str, list[str]],
    ordered_tag_ids: list[str],
    scale: DiscreteColorScale[str],
) -> list[list[int]]:
    """Assign categories in legend order, preserving the projection's sample order."""
    sample_keys = [str(sample_id) for sample_id in sample_ids]
    categories: dict[str, list[int]] = {sample_id: [] for sample_id in sample_keys}
    # Iterating in legend order produces sorted colors, including repeated Other
    # slots when a sample carries multiple tags grouped into that category.
    for tag_id in ordered_tag_ids:
        category = scale.value_to_category(tag_id)
        assert category is not None
        for sample_id in samples_by_tag[tag_id]:
            sample_categories = categories.get(sample_id)
            if sample_categories is not None:
                sample_categories.append(category)
    return [categories[sample_id] for sample_id in sample_keys]


def _group_memberships(
    session: Session, tag_ids: list[UUID], matching_sample_ids: set[UUID] | None
) -> _GroupedMemberships:
    """Group unique links and count filter-matching samples in one pass."""
    matching_keys = (
        None if matching_sample_ids is None else {str(sid) for sid in matching_sample_ids}
    )
    samples_by_tag: dict[str, list[str]] = {}
    counts: Counter[str] = Counter()
    for sample_id, tag_id in iter_sample_memberships.iter_sample_memberships(
        session=session, tag_ids=tag_ids
    ):
        samples_by_tag.setdefault(tag_id, []).append(sample_id)
        if matching_keys is None or sample_id in matching_keys:
            counts[tag_id] += 1
    return _GroupedMemberships(samples_by_tag=samples_by_tag, matching_counts=counts)
