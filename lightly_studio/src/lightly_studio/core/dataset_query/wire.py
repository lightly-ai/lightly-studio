"""Wire-format Pydantic models and deserialisation for dataset queries.

The wire format is the canonical JSON representation shared by the frontend
query builder and the Python ``DatasetQuery`` API.  It maps 1-to-1 to the
``MatchExpression`` class hierarchy and can be round-tripped via
``MatchExpression.to_wire()`` / ``deserialize()``.

Supported node types
--------------------
``field``
    A scalar comparison:
    ``{"type": "field", "field": "image.width", "op": ">", "value": 500}``

    Supported field names:
        image.width, image.height, image.file_name, image.file_path_abs,
        image.created_at
        video.file_name, video.width, video.height, video.file_path_abs,
        video.fps, video.duration_s   (reserved - not yet exposed in the frontend)

    Supported ops for ordinal fields:  ``>``, ``>=``, ``<``, ``<=``, ``==``, ``!=``
    Supported ops for comparable fields (strings): ``==``, ``!=``

``tags_contains``
    Tag membership check: ``{"type": "tags_contains", "tag": "outdoor"}``

``and``
    Logical AND: ``{"type": "and", "terms": [...]}``

``or``
    Logical OR: ``{"type": "or", "terms": [...]}``

``not``
    Logical NOT: ``{"type": "not", "term": {...}}``
    (Python API only - the frontend query builder does not emit this node.)
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union, cast

from pydantic import BaseModel, Field
from sqlalchemy import ColumnElement

from lightly_studio.core.dataset_query.boolean_expression import AND, NOT, OR
from lightly_studio.core.dataset_query.field import ComparableField, OrdinalField
from lightly_studio.core.dataset_query.field_expression import (
    ComparableFieldExpression,
    ComparisonOperator,
    OrdinalFieldExpression,
)
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.core.dataset_query.tags_expression import TagsContainsExpression
from lightly_studio.core.dataset_query.video_sample_field import VideoSampleField

# ---------------------------------------------------------------------------
# Field registry
# ---------------------------------------------------------------------------

_FIELD_REGISTRY: dict[str, Any] = {
    # image fields
    "image.file_name": ImageSampleField.file_name,
    "image.width": ImageSampleField.width,
    "image.height": ImageSampleField.height,
    "image.file_path_abs": ImageSampleField.file_path_abs,
    "image.created_at": ImageSampleField.created_at,
    # video fields (reserved for future frontend support)
    "video.file_name": VideoSampleField.file_name,
    "video.width": VideoSampleField.width,
    "video.height": VideoSampleField.height,
    "video.file_path_abs": VideoSampleField.file_path_abs,
    "video.fps": VideoSampleField.fps,
    "video.duration_s": VideoSampleField.duration_s,
}


# ---------------------------------------------------------------------------
# Pydantic wire models
# ---------------------------------------------------------------------------

class WireField(BaseModel):
    """A scalar field comparison."""

    type: Literal["field"] = "field"
    field: str
    op: Literal[">", ">=", "<", "<=", "==", "!="]
    value: float | int | str


class WireTagsContains(BaseModel):
    """A tag membership check."""

    type: Literal["tags_contains"] = "tags_contains"
    tag: str


class WireAnd(BaseModel):
    """Logical AND of a list of expressions."""

    type: Literal["and"] = "and"
    terms: list[WireExpression]


class WireOr(BaseModel):
    """Logical OR of a list of expressions."""

    type: Literal["or"] = "or"
    terms: list[WireExpression]


class WireNot(BaseModel):
    """Logical NOT of a single expression."""

    type: Literal["not"] = "not"
    term: WireExpression


WireExpression = Annotated[
    Union[WireField, WireTagsContains, WireAnd, WireOr, WireNot],
    Field(discriminator="type"),
]

# Required so that the forward references inside WireAnd/WireOr/WireNot resolve.
WireAnd.model_rebuild()
WireOr.model_rebuild()
WireNot.model_rebuild()


# ---------------------------------------------------------------------------
# Deserialisation
# ---------------------------------------------------------------------------

def deserialize(expr: WireExpression) -> ColumnElement[bool]:
    """Convert a ``WireExpression`` to a SQLAlchemy WHERE condition.

    Args:
        expr: The wire expression received from the frontend or built via
              ``MatchExpression.to_wire()``.

    Returns:
        A SQLAlchemy ``ColumnElement[bool]`` ready to be passed to
        ``query.where(...)``.

    Raises:
        ValueError: If a field name is not in the registry.
    """
    return _to_match_expression(expr).get()


def _to_match_expression(expr: Any) -> MatchExpression:
    """Recursively reconstruct a ``MatchExpression`` from a wire node."""
    if isinstance(expr, WireField):
        field = _FIELD_REGISTRY.get(expr.field)
        if field is None:
            raise ValueError(f"[WireExpression] Unknown field: {expr.field!r}")
        if isinstance(field, OrdinalField):
            return OrdinalFieldExpression(field=field, operator=expr.op, value=expr.value)
        if isinstance(field, ComparableField):
            if expr.op not in ("==", "!="):
                raise ValueError(
                    f"[WireExpression] Field {expr.field!r} only supports "
                    f"== and !=, got {expr.op!r}"
                )
            return ComparableFieldExpression(
                field=field, operator=cast(ComparisonOperator, expr.op), value=expr.value
            )
        raise ValueError(f"[WireExpression] Unsupported field type for {expr.field!r}")

    if isinstance(expr, WireTagsContains):
        return TagsContainsExpression(tag_name=expr.tag)

    if isinstance(expr, WireAnd):
        return AND(*(_to_match_expression(t) for t in expr.terms))

    if isinstance(expr, WireOr):
        return OR(*(_to_match_expression(t) for t in expr.terms))

    if isinstance(expr, WireNot):
        return NOT(_to_match_expression(expr.term))

    raise ValueError(f"[WireExpression] Unrecognised node type: {type(expr)!r}")
