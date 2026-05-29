"""Annotation-based coloring helpers for 2D embedding plots."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlmodel import Session

from lightly_studio.api.routes.api.embedding_coloring import coloring_helpers
from lightly_studio.api.routes.api.embedding_coloring.coloring_helpers import DiscreteColorScale
from lightly_studio.resolvers import annotation_label_resolver, annotation_resolver


def build_annotation_color_maps(
    session: Session,
    annotation_label_ids: list[UUID],
    sample_ids: list[UUID],
) -> tuple[list[list[int]], dict[int, str]]:
    """Build color categories and a legend for annotation-based sample coloring.

    Each annotation label gets a consecutive color category (starting at 2). All requested
    labels appear in the legend even if no samples match.

    Args:
        session: Database session.
        annotation_label_ids: Ordered label IDs that define coloring priority.
        sample_ids: Sample IDs in the order for which to build color categories.

    Returns:
        A tuple of `(color_categories, color_legend)` for the provided samples.
        The length of `color_categories` is the number of samples; each entry is
        the list of that sample's color categories, sorted ascending. The `color_legend`
        is a mapping from color ID to a human-readable string.
    """
    names = annotation_label_resolver.names_by_ids(session=session, ids=annotation_label_ids)
    annotations = annotation_resolver.get_all_by_parent_sample_ids(
        session=session, parent_sample_ids=sample_ids
    )

    # Build a lookup: parent_sample_id → set of annotation_label_ids.
    sample_to_labels: dict[UUID, set[UUID]] = defaultdict(set)
    requested = set(annotation_label_ids)
    for ann in annotations:
        if ann.annotation_label_id in requested:
            sample_to_labels[ann.parent_sample_id].add(ann.annotation_label_id)

    scale = DiscreteColorScale.from_values(
        values=annotation_label_ids,
        format_fn=lambda lid: names.get(str(lid), str(lid)),
    )

    return coloring_helpers.assign_color_category_lists(
        sample_ids=sample_ids,
        sample_to_values=sample_to_labels,
        scale=scale,
    )
