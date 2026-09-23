from __future__ import annotations

from uuid import uuid4

from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.image_resolver import annotation_count_helpers
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter


def test_get_annotation_collection_ids__no_filter() -> None:
    result = annotation_count_helpers.get_annotation_collection_ids(image_filter=None)

    assert result is None


def test_get_annotation_collection_ids__filter_without_annotations_filter() -> None:
    image_filter = ImageFilter(sample_filter=SampleFilter())

    result = annotation_count_helpers.get_annotation_collection_ids(image_filter=image_filter)

    assert result is None


def test_get_annotation_collection_ids__returns_collection_ids() -> None:
    collection_id = uuid4()
    image_filter = ImageFilter(
        sample_filter=SampleFilter(
            annotations_filter=AnnotationsFilter(collection_ids=[collection_id])
        )
    )

    result = annotation_count_helpers.get_annotation_collection_ids(image_filter=image_filter)

    assert result == [collection_id]
