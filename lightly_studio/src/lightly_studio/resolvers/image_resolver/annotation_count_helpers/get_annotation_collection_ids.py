"""Extract annotation source collection IDs from an image filter."""

from __future__ import annotations

from uuid import UUID

from lightly_studio.resolvers.image_filter import ImageFilter


def get_annotation_collection_ids(image_filter: ImageFilter | None) -> list[UUID] | None:
    """Return the annotation source collection IDs from the filter, or None if unrestricted."""
    sample_filter = image_filter.sample_filter if image_filter is not None else None
    if sample_filter is None or sample_filter.annotations_filter is None:
        return None
    return sample_filter.annotations_filter.collection_ids
