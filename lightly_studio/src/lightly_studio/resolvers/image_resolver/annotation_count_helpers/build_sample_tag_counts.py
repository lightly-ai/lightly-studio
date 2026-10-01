"""Assemble per-tag annotation count series from query results."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID

from lightly_studio.resolvers.image_resolver.annotation_count_types import (
    AnnotationClassCount,
    SampleTagAnnotationCounts,
)


def build_sample_tag_counts(
    sample_tag_ids: Sequence[UUID],
    sample_tags: Mapping[UUID, str],
    class_names: Sequence[str],
    grouped_counts: Mapping[tuple[UUID, str], int],
) -> list[SampleTagAnnotationCounts]:
    """Assemble zero-filled per-tag count series from query results."""
    return [
        SampleTagAnnotationCounts(
            sample_tag_id=tag_id,
            sample_tag_name=sample_tags[tag_id],
            counts=tuple(
                AnnotationClassCount(
                    label_name=class_name,
                    count=grouped_counts.get((tag_id, class_name), 0),
                )
                for class_name in class_names
            ),
        )
        for tag_id in sample_tag_ids
    ]
