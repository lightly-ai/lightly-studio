"""Assemble per-tag annotation count series from query results."""

from __future__ import annotations

from uuid import UUID

from lightly_studio.resolvers.image_resolver.annotation_count_types import (
    AnnotationClassCount,
    SampleTagAnnotationCounts,
)


def build_sample_tag_counts(
    sample_tag_ids: list[UUID],
    sample_tags: dict[UUID, str],
    class_names: list[str],
    grouped_counts: dict[tuple[UUID, str], int],
) -> list[SampleTagAnnotationCounts]:
    """Assemble zero-filled per-tag count series from query results."""
    return [
        SampleTagAnnotationCounts(
            sample_tag_id=tag_id,
            sample_tag_name=sample_tags[tag_id],
            counts=[
                AnnotationClassCount(
                    label_name=class_name,
                    count=grouped_counts.get((tag_id, class_name), 0),
                )
                for class_name in class_names
            ],
        )
        for tag_id in sample_tag_ids
    ]
