"""Utility for deserializing DSL queries from JSON."""

from __future__ import annotations

from typing import Any

from lightly_studio.core.dataset_query.boolean_expression import AND, NOT, OR
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.core.dataset_query.object_detection_expression import (
    ObjectDetectionField,
    ObjectDetectionQuery,
)
from lightly_studio.core.dataset_query.video_sample_field import VideoSampleField


class DSLDeserializer:
    """Deserializes a JSON-based DSL query into MatchExpression objects."""

    def __init__(self, sample_type: str = "image") -> None:
        """Initialize with sample type to determine default field mapping.

        Args:
            sample_type: Type of samples being queried ("image", "video", or "group").
        """
        self.sample_type = sample_type
        self._field_registry = {
            "sample": ImageSampleField if sample_type == "image" else VideoSampleField,
            "object_detection": ObjectDetectionField,
        }

    def deserialize(self, data: dict[str, Any], context: str = "sample") -> MatchExpression:
        """Recursively deserialize JSON query data.

        Args:
            data: The JSON dictionary representing a query node.
            context: The current query context (e.g., "sample", "object_detection").

        Returns:
            A MatchExpression representing the query.
        """
        kind = data.get("kind")

        if kind == "AND":
            return AND(*(self.deserialize(t, context) for t in data["terms"]))
        if kind == "OR":
            return OR(*(self.deserialize(t, context) for t in data["terms"]))
        if kind == "NOT":
            return NOT(self.deserialize(data["term"], context))

        if kind == "COMPARISON":
            return self._handle_comparison(data, context)

        if kind == "TAGS_CONTAINS":
            # Only valid in sample context
            return ImageSampleField.tags.contains(data["tag_name"])

        if kind == "ANNOTATION_QUERY":
            return self._handle_annotation_query(data)

        raise ValueError(f"Unknown DSL node kind: {kind}")

    def _handle_comparison(self, data: dict[str, Any], context: str) -> MatchExpression:
        field_name = data["field"]
        operator = data["operator"]
        value = data["value"]

        field_registry = self._field_registry.get(context)
        if not field_registry:
            raise ValueError(f"Unknown context for field lookup: {context}")

        field_obj = getattr(field_registry, field_name, None)
        if field_obj is None:
            raise ValueError(f"Field '{field_name}' not found in context '{context}'")

        # Map string operators to Python comparisons
        if operator == "==":
            return field_obj == value
        if operator == "!=":
            return field_obj != value
        if operator == ">":
            return field_obj > value
        if operator == "<":
            return field_obj < value
        if operator == ">=":
            return field_obj >= value
        if operator == "<=":
            return field_obj <= value

        raise ValueError(f"Unsupported operator: {operator}")

    def _handle_annotation_query(self, data: dict[str, Any]) -> MatchExpression:
        annotation_type = data["annotation_type"]
        criterion = self.deserialize(data["criterion"], context=annotation_type)

        if annotation_type == "object_detection":
            return ObjectDetectionQuery.match(criterion)

        raise ValueError(f"Unsupported annotation type: {annotation_type}")
