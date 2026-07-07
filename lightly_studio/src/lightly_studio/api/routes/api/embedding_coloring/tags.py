"""Tag-based coloring helpers for 2D embedding plots."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.api.routes.api.embedding_coloring import coloring_helpers
from lightly_studio.api.routes.api.embedding_coloring.coloring_helpers import DiscreteColorScale
from lightly_studio.resolvers import tag_resolver


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
    names = tag_resolver.get_names_by_ids(session=session, tag_ids=tag_ids)
    sample_to_tags = tag_resolver.get_tags_by_sample(session=session, tag_ids=tag_ids)

    ordered_tag_ids = coloring_helpers.order_values_by_frequency(
        sample_to_values=sample_to_tags,
        matching_sample_ids=matching_sample_ids,
        format_fn=lambda tid: names.get(tid, str(tid)),
    )
    scale = DiscreteColorScale.from_values(
        values=ordered_tag_ids,
        format_fn=lambda tid: names.get(tid, str(tid)),
    )

    return coloring_helpers.assign_color_categories(
        sample_ids=sample_ids,
        sample_to_values=sample_to_tags,
        scale=scale,
    )
