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
    fulfils_filter: list[int],
) -> tuple[list[int], dict[int, str]]:
    """Build color categories and a legend for tag-based sample coloring.

    Each selected tag gets a consecutive color category (starting at 2) in the
    order given by *tag_ids*.  When a sample belongs to multiple selected tags
    the **first match wins** — it receives the category of the earliest tag in
    the list.

    Args:
        session: Database session.
        tag_ids: Ordered tag IDs that define coloring priority.
        sample_ids: Sample IDs in the order for which to build color categories.
        fulfils_filter: Per-sample filter flags where 0 means filtered out.

    Returns:
        A tuple of `(color_categories, color_legend)` for the provided samples. The
        length of `color_categories` is the number of samples. The `color_legend` is a mapping
        from color ID to a human-readable string.
    """
    names = tag_resolver.get_names_by_ids(session=session, tag_ids=tag_ids)
    sample_to_tags = tag_resolver.get_tags_by_sample(session=session, tag_ids=tag_ids)

    scale = DiscreteColorScale.from_values(
        values=tag_ids,
        format_fn=lambda tid: names.get(tid, str(tid)),
    )

    # First-match-wins: map each sample to its earliest matching tag.
    sample_to_value: dict[UUID, UUID] = {}
    for sid, sample_tags in sample_to_tags.items():
        for tid in tag_ids:
            if tid in sample_tags:
                sample_to_value[sid] = tid
                break

    return coloring_helpers.assign_color_categories(
        sample_ids=sample_ids,
        fulfils_filter=fulfils_filter,
        sample_to_value=sample_to_value,
        scale=scale,
    )
