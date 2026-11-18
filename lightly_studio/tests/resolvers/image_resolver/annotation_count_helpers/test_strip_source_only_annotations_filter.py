from __future__ import annotations

from uuid import UUID

import pytest

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.embedding_region import EmbeddingRegion, Point2D
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.image_filter import FilterDimensions, ImageFilter
from lightly_studio.resolvers.image_resolver import annotation_count_helpers
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter

SOURCE_ID = UUID("00000000-0000-0000-0000-000000000001")
LABEL_ID = UUID("00000000-0000-0000-0000-000000000002")
TAG_ID = UUID("00000000-0000-0000-0000-000000000003")
SAMPLE_ID = UUID("00000000-0000-0000-0000-000000000004")


@pytest.mark.parametrize(
    "image_filter",
    [
        None,
        ImageFilter(),
        ImageFilter(sample_filter=SampleFilter()),
    ],
)
def test_strip_source_only_annotations_filter__nothing_to_strip(
    image_filter: ImageFilter | None,
) -> None:
    result = annotation_count_helpers.strip_source_only_annotations_filter(
        image_filter=image_filter
    )

    assert result is image_filter


@pytest.mark.parametrize(
    "annotations_filter",
    [
        AnnotationsFilter(collection_ids=[SOURCE_ID]),
        AnnotationsFilter(collection_ids=[]),
        AnnotationsFilter(),
        # The frontend can send unused fields as explicit nulls.
        AnnotationsFilter.model_validate(
            {
                "collection_ids": [str(SOURCE_ID)],
                "annotation_label_ids": None,
                "tag_ids": None,
            }
        ),
    ],
)
def test_strip_source_only_annotations_filter__strips(
    annotations_filter: AnnotationsFilter,
) -> None:
    original_collection_ids = annotations_filter.collection_ids
    sample_filter = SampleFilter(tag_ids=[TAG_ID], annotations_filter=annotations_filter)
    image_filter = ImageFilter(sample_filter=sample_filter, width=FilterDimensions(min=10))

    result = annotation_count_helpers.strip_source_only_annotations_filter(
        image_filter=image_filter
    )

    assert result is not None
    assert result is not image_filter
    assert result.sample_filter is not None
    assert result.sample_filter is not sample_filter
    assert result.sample_filter.annotations_filter is None
    assert result.sample_filter.tag_ids == [TAG_ID]
    assert result.width == FilterDimensions(min=10)
    # The caller's filter keeps its source selection.
    assert sample_filter.annotations_filter is annotations_filter
    assert annotations_filter.collection_ids == original_collection_ids


@pytest.mark.parametrize(
    "annotations_filter",
    [
        AnnotationsFilter(collection_ids=[SOURCE_ID], annotation_label_ids=[LABEL_ID]),
        AnnotationsFilter(collection_ids=[SOURCE_ID], annotation_label_ids=[]),
        AnnotationsFilter(
            collection_ids=[SOURCE_ID], annotation_types=[AnnotationType.OBJECT_DETECTION]
        ),
        AnnotationsFilter(collection_ids=[SOURCE_ID], tag_ids=[TAG_ID]),
        AnnotationsFilter(collection_ids=[SOURCE_ID], sample_ids=[SAMPLE_ID]),
        AnnotationsFilter(collection_ids=[SOURCE_ID], region_sample_ids=[]),
        AnnotationsFilter(collection_ids=[SOURCE_ID], region_sample_ids=[SAMPLE_ID]),
        AnnotationsFilter(
            collection_ids=[SOURCE_ID],
            embedding_region=EmbeddingRegion(
                polygon=[Point2D(x=0, y=0), Point2D(x=1, y=0), Point2D(x=1, y=1)]
            ),
        ),
    ],
)
def test_strip_source_only_annotations_filter__keeps(
    annotations_filter: AnnotationsFilter,
) -> None:
    image_filter = ImageFilter(sample_filter=SampleFilter(annotations_filter=annotations_filter))

    result = annotation_count_helpers.strip_source_only_annotations_filter(
        image_filter=image_filter
    )

    assert result is image_filter


def test_strip_source_only_annotations_filter__unresolved_embedding_region() -> None:
    # Called before resolve_embedding_region: the copy would lose the region.
    image_filter = ImageFilter(
        sample_filter=SampleFilter(
            embedding_region=EmbeddingRegion(
                polygon=[Point2D(x=0, y=0), Point2D(x=1, y=0), Point2D(x=1, y=1)]
            ),
            annotations_filter=AnnotationsFilter(collection_ids=[SOURCE_ID]),
        )
    )

    with pytest.raises(RuntimeError, match=r"resolve_embedding_region"):
        annotation_count_helpers.strip_source_only_annotations_filter(image_filter=image_filter)
