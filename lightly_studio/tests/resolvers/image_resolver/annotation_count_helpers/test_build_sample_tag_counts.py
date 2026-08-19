from __future__ import annotations

from uuid import uuid4

from lightly_studio.resolvers.image_resolver import annotation_count_helpers
from lightly_studio.resolvers.image_resolver.annotation_count_types import AnnotationClassCount


def test_build_sample_tag_counts__preserves_order_and_zero_fills() -> None:
    tag_a, tag_b = uuid4(), uuid4()
    sample_tags = {tag_a: "tag-a", tag_b: "tag-b"}
    class_names = ["cat", "dog"]
    grouped_counts = {(tag_a, "dog"): 3, (tag_b, "cat"): 1}

    result = annotation_count_helpers.build_sample_tag_counts(
        sample_tag_ids=[tag_b, tag_a],
        sample_tags=sample_tags,
        class_names=class_names,
        grouped_counts=grouped_counts,
    )

    assert [r.sample_tag_id for r in result] == [tag_b, tag_a]
    assert result[0].sample_tag_name == "tag-b"
    assert result[0].counts == (
        AnnotationClassCount(label_name="cat", count=1),
        AnnotationClassCount(label_name="dog", count=0),
    )
    assert result[1].sample_tag_name == "tag-a"
    assert result[1].counts == (
        AnnotationClassCount(label_name="cat", count=0),
        AnnotationClassCount(label_name="dog", count=3),
    )


def test_build_sample_tag_counts__empty_class_names() -> None:
    tag_id = uuid4()

    result = annotation_count_helpers.build_sample_tag_counts(
        sample_tag_ids=[tag_id],
        sample_tags={tag_id: "my-tag"},
        class_names=[],
        grouped_counts={},
    )

    assert result[0].counts == ()
