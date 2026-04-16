"""Registry mapping field names to field objects for query compilation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from sqlmodel import col

from lightly_studio.core.dataset_query.field import ComparableField
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.models.annotation_label import AnnotationLabelTable

FieldType = Literal["number", "string", "datetime"]
FieldKind = Literal["direct", "annotation_label"]

_ORDINAL_OPS = [">", "<", ">=", "<=", "==", "!="]
_STRING_OPS = ["==", "!=", "contains", "in"]


@dataclass
class FieldInfo:
    """Metadata and field object for a single registered field."""

    name: str
    field_type: FieldType
    operators: list[str]
    kind: FieldKind
    field: Any  # OrdinalField or ComparableField instance


class FieldRegistry:
    """Maps field names to FieldInfo objects for two contexts: sample and annotation."""

    def __init__(self) -> None:
        """Initialise the registry with built-in image sample and annotation fields."""
        self._sample_fields: dict[str, FieldInfo] = {
            "width": FieldInfo("width", "number", _ORDINAL_OPS, "direct", ImageSampleField.width),
            "height": FieldInfo(
                "height", "number", _ORDINAL_OPS, "direct", ImageSampleField.height
            ),
            "file_name": FieldInfo(
                "file_name", "string", _STRING_OPS, "direct", ImageSampleField.file_name
            ),
            "file_path_abs": FieldInfo(
                "file_path_abs",
                "string",
                _STRING_OPS,
                "direct",
                ImageSampleField.file_path_abs,
            ),
            "created_at": FieldInfo(
                "created_at", "datetime", _ORDINAL_OPS, "direct", ImageSampleField.created_at
            ),
        }
        self._annotation_fields: dict[str, FieldInfo] = {
            "label": FieldInfo(
                "label",
                "string",
                ["==", "!="],
                "annotation_label",
                ComparableField(col(AnnotationLabelTable.annotation_label_name)),
            ),
        }

    def resolve(self, field_ref: list[str], context: str) -> FieldInfo:
        """Return the FieldInfo for a field reference in the given context.

        Args:
            field_ref: Dot-separated field path as a list of parts.
            context: ``"sample"`` or ``"annotation"``.

        Raises:
            ValueError: If the field is unknown in the given context.
        """
        name = ".".join(field_ref)
        if context == "sample":
            if name in self._sample_fields:
                return self._sample_fields[name]
            raise ValueError(f"Unknown field in sample context: {name!r}")
        if context == "annotation":
            if name in self._annotation_fields:
                return self._annotation_fields[name]
            raise ValueError(f"Unknown field in annotation context: {name!r}")
        raise ValueError(f"Unknown context: {context!r}")

    def get_schema(self) -> dict[str, Any]:
        """Return a serializable catalogue of all registered fields."""

        def _to_dict(fi: FieldInfo) -> dict[str, Any]:
            return {"name": fi.name, "field_type": fi.field_type, "operators": fi.operators}

        return {
            "fields": [_to_dict(fi) for fi in self._sample_fields.values()],
            "subcontexts": {
                "annotation": [_to_dict(fi) for fi in self._annotation_fields.values()],
            },
        }
