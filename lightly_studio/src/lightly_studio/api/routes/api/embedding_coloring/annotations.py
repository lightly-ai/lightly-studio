"""Annotation-based coloring helpers for 2D embedding plots."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio import db_array
from lightly_studio.api.routes.api.embedding_coloring import coloring_helpers
from lightly_studio.api.routes.api.embedding_coloring.coloring_helpers import DiscreteColorScale
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.resolvers import annotation_label_resolver, annotation_resolver


def build_annotation_color_maps(
    session: Session,
    annotation_label_ids: list[UUID],
    sample_ids: list[UUID],
    matching_sample_ids: set[UUID] | None,
) -> tuple[list[list[int]], dict[int, str]]:
    """Build color categories and a legend for annotation-based sample coloring.

    When more labels are selected than fit in the legend, the labels carried by
    the most filter-matching samples each get a dedicated color category and the
    rest are merged into a single "Other" category. Labels with no matching
    sample are omitted from the legend entirely.

    Args:
        session: Database session.
        annotation_label_ids: Label IDs to color by.
        sample_ids: Sample IDs in the order for which to build color categories.
        matching_sample_ids: Sample IDs matching the active filter. Labels are
            prioritized by their frequency among these samples. ``None`` counts
            all samples.

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

    # LIG-9521 prototype: when the colored samples are annotations themselves (annotation
    # collection), each sample carries its own label rather than labels of child annotations.
    own_annotations = session.exec(
        select(AnnotationBaseTable).where(
            db_array.in_array(column=col(AnnotationBaseTable.sample_id), values=sample_ids)
        )
    ).all()
    for ann in own_annotations:
        if ann.annotation_label_id in requested:
            sample_to_labels[ann.sample_id].add(ann.annotation_label_id)

    ordered_label_ids = coloring_helpers.order_values_by_frequency(
        sample_to_values=sample_to_labels,
        matching_sample_ids=matching_sample_ids,
        format_fn=lambda lid: names.get(str(lid), str(lid)),
    )
    scale = DiscreteColorScale.from_values(
        values=ordered_label_ids,
        format_fn=lambda lid: names.get(str(lid), str(lid)),
    )

    return coloring_helpers.assign_color_categories(
        sample_ids=sample_ids,
        sample_to_values=sample_to_labels,
        scale=scale,
    )
