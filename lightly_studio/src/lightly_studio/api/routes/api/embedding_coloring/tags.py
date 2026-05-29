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
) -> tuple[list[list[int]], dict[int, str]]:
    """Build color categories and a legend for tag-based sample coloring.

    Each selected tag gets a consecutive color category (starting at 2) in the
    order given by *tag_ids*.  When a sample belongs to multiple selected tags it
    receives **all** their categories.

    Args:
        session: Database session.
        tag_ids: Ordered tag IDs that define coloring priority.
        sample_ids: Sample IDs in the order for which to build color categories.

    Returns:
        A tuple of `(color_categories, color_legend)` for the provided samples. The
        length of `color_categories` is the number of samples; each entry is the
        list of that sample's color categories. The `color_legend` is a mapping
        from color ID to a human-readable string.
    """
    names = tag_resolver.get_names_by_ids(session=session, tag_ids=tag_ids)
    sample_to_tags = tag_resolver.get_tags_by_sample(session=session, tag_ids=tag_ids)

    scale = DiscreteColorScale.from_values(
        values=tag_ids,
        format_fn=lambda tid: names.get(tid, str(tid)),
    )

    return coloring_helpers.assign_color_category_lists(
        sample_ids=sample_ids,
        sample_to_values=sample_to_tags,
        scale=scale,
    )
