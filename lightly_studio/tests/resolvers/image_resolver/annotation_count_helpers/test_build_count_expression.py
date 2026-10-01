from __future__ import annotations

from lightly_studio.resolvers.image_resolver import annotation_count_helpers
from lightly_studio.resolvers.image_resolver.annotation_count_types import AnnotationCountMode


def test_build_count_expression__objects_mode() -> None:
    expr = annotation_count_helpers.build_count_expression(AnnotationCountMode.OBJECTS)

    assert "distinct" not in str(expr).lower()
    assert "sample_id" in str(expr)
    assert "parent_sample_id" not in str(expr)


def test_build_count_expression__samples_mode() -> None:
    expr = annotation_count_helpers.build_count_expression(AnnotationCountMode.SAMPLES)

    assert "distinct" in str(expr).lower()
    assert "parent_sample_id" in str(expr)
