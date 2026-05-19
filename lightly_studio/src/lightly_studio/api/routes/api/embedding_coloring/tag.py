"""Tag-based coloring helpers for 2D embedding plots."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.sample import SampleTagLinkTable
from lightly_studio.models.tag import TagTable


def build_tag_color_maps(
    session: Session,
    tag_ids: list[UUID],
    sample_ids: list[UUID],
    fulfils_filter: list[int],
    start_cat: int,
) -> tuple[list[int], dict[int, str]]:
    """Build color categories and a legend for tag-based sample coloring.

    Each tag in *tag_ids* is assigned a consecutive color category starting at
    *start_cat*.  When a sample belongs to multiple requested tags the lowest
    category wins.

    Args:
        session: Database session.
        tag_ids: Tags to color by, in priority order.
        sample_ids: Sample IDs in the order for which to build color categories.
        fulfils_filter: Per-sample filter flags where 0 means filtered out.
        start_cat: First category ID available for tag values (usually 2).

    Returns:
        A tuple of ``(color_categories, color_legend)``.
    """
    tag_names = _query_tag_names(session=session, tag_ids=tag_ids)
    memberships = _query_sample_tag_memberships(session=session, tag_ids=tag_ids)

    # Map each requested tag to its category.
    tag_id_to_cat = {tid: start_cat + i for i, tid in enumerate(tag_ids)}

    # For each sample keep only the lowest category (first-match-wins).
    sample_to_cat: dict[UUID, int] = {}
    for sample_id, tag_id in memberships:
        cat = tag_id_to_cat[tag_id]
        if sample_id not in sample_to_cat or cat < sample_to_cat[sample_id]:
            sample_to_cat[sample_id] = cat

    # Assign categories respecting the filter.
    color_categories: list[int] = []
    for i, sid in enumerate(sample_ids):
        if fulfils_filter[i] == 0:
            color_categories.append(0)
        elif sid in sample_to_cat:
            color_categories.append(sample_to_cat[sid])
        else:
            color_categories.append(1)

    legend = {start_cat + i: tag_names.get(tid, str(tid)) for i, tid in enumerate(tag_ids)}
    return color_categories, legend


def _query_tag_names(session: Session, tag_ids: list[UUID]) -> dict[UUID, str]:
    """Return ``{tag_id: name}`` for the requested tags."""
    if not tag_ids:
        return {}
    stmt = select(TagTable.tag_id, TagTable.name).where(TagTable.tag_id.in_(tag_ids))  # type: ignore[attr-defined]
    return dict(session.exec(stmt).all())


def _query_sample_tag_memberships(
    session: Session,
    tag_ids: list[UUID],
) -> list[tuple[UUID, UUID]]:
    """Return ``(sample_id, tag_id)`` rows for the requested tags."""
    if not tag_ids:
        return []
    stmt = select(SampleTagLinkTable.sample_id, SampleTagLinkTable.tag_id).where(
        SampleTagLinkTable.tag_id.in_(tag_ids)  # type: ignore[union-attr]
    )
    return list(session.exec(stmt).all())  # type: ignore[arg-type]
