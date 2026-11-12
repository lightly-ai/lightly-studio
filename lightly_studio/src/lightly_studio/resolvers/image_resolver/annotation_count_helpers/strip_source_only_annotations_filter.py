"""Remove an annotations filter that only selects annotation sources."""

from __future__ import annotations

from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.image_filter import ImageFilter

_SOURCE_FIELD = "collection_ids"


def strip_source_only_annotations_filter(image_filter: ImageFilter | None) -> ImageFilter | None:
    """Return a copy of the filter without an annotations filter that only selects sources.

    The count queries restrict annotations to the selected sources with their own join. An
    annotations filter that only selects sources then adds a parent-sample IN that removes no
    row, but makes the database plan the count badly.

    Call this after ``resolve_embedding_region``, which writes the region sample IDs into the
    input filter. Read the source IDs from the input filter, because the copy has none.

    Args:
        image_filter: The image filter of the count request.

    Returns:
        A copy without the annotations filter if every annotations filter field except
        ``collection_ids`` has its default value. Otherwise the input filter.

    Raises:
        RuntimeError: If the filter has an embedding region that is not resolved yet.
    """
    sample_filter = image_filter.sample_filter if image_filter is not None else None
    if image_filter is None or sample_filter is None:
        return image_filter
    if sample_filter.embedding_region is not None and sample_filter.region_sample_ids is None:
        # A copy taken now would not get the region sample IDs.
        raise RuntimeError("Call resolve_embedding_region before stripping the filter.")
    if sample_filter.annotations_filter is None:
        return image_filter
    if not _is_source_only(annotations_filter=sample_filter.annotations_filter):
        return image_filter
    # A shallow copy shares the sample filter. Copy it too, so that the input keeps its sources.
    return image_filter.model_copy(
        update={"sample_filter": sample_filter.model_copy(update={"annotations_filter": None})}
    )


def _is_source_only(annotations_filter: AnnotationsFilter) -> bool:
    # Compare all fields, so that a field added later keeps the filter.
    exclude = {_SOURCE_FIELD}
    return annotations_filter.model_dump(exclude=exclude) == AnnotationsFilter().model_dump(
        exclude=exclude
    )
