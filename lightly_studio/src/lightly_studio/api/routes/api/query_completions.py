"""Completion metadata endpoint for the Monaco Python query editor.

The response is derived by introspecting the real DatasetQuery objects so it
never drifts from the actual API surface.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from lightly_studio.core.dataset_query.boolean_expression import AND, NOT, OR
from lightly_studio.core.dataset_query.field import ComparableField, OrdinalField
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.tags_expression import TagsAccessor

query_completions_router = APIRouter()

# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

FieldKind = Literal["NumericalField", "ComparableField", "TagsAccessor"]


class MethodMeta(BaseModel):
    """Metadata for a method callable on a field (e.g. TagsAccessor.contains)."""

    name: str
    detail: str
    insert_text: str
    doc: str


class FieldMeta(BaseModel):
    """Metadata for a single queryable field on a namespace class."""

    name: str
    kind: FieldKind
    operators: list[str]
    methods: list[MethodMeta]
    doc: str


class NamespaceMeta(BaseModel):
    """Metadata for a top-level namespace (e.g. ImageSampleField)."""

    name: str
    doc: str
    fields: list[FieldMeta]


class FunctionMeta(BaseModel):
    """Metadata for a top-level combinator function (AND, OR, NOT)."""

    name: str
    signature: str
    doc: str


class QueryCompletionsResponse(BaseModel):
    """All completion metadata needed to drive the Monaco provider."""

    namespaces: list[NamespaceMeta]
    functions: list[FunctionMeta]


# ---------------------------------------------------------------------------
# Operator sets
# ---------------------------------------------------------------------------

_ORDINAL_OPS = [">", ">=", "<", "<=", "==", "!="]
_COMPARABLE_OPS = ["==", "!="]
_TAGS_OPS: list[str] = []  # TagsAccessor exposes .contains(), not operators
_TAGS_METHODS = [
    MethodMeta(
        name="contains",
        detail="contains(tag_name: str) -> MatchExpression",
        insert_text='contains("$1")',
        doc="Match samples that have this tag.",
    )
]


def _field_kind(field: object) -> FieldKind:
    if isinstance(field, OrdinalField):
        return "NumericalField"
    if isinstance(field, ComparableField):
        return "ComparableField"
    if isinstance(field, TagsAccessor):
        return "TagsAccessor"
    raise TypeError(f"Unknown field type: {type(field)}")


def _field_ops(field: object) -> list[str]:
    if isinstance(field, TagsAccessor):
        return _TAGS_OPS
    if isinstance(field, OrdinalField):
        return _ORDINAL_OPS
    if isinstance(field, ComparableField):
        return _COMPARABLE_OPS
    return []


def _field_doc(name: str, field: object) -> str:
    if isinstance(field, TagsAccessor):
        return f"Tag filter — use {name}.contains(tag_name: str)"
    if isinstance(field, OrdinalField):
        return f"Ordinal field; supports {', '.join(_ORDINAL_OPS)}"
    if isinstance(field, ComparableField):
        return f"String field; supports {', '.join(_COMPARABLE_OPS)}"
    return ""


def _introspect_namespace(cls: type, cls_name: str) -> NamespaceMeta:
    """Build NamespaceMeta by inspecting class-level attributes."""
    fields: list[FieldMeta] = []
    for attr_name in vars(cls):
        if attr_name.startswith("_"):
            continue
        field = getattr(cls, attr_name)
        if not isinstance(field, (OrdinalField, ComparableField, TagsAccessor)):
            continue
        fields.append(
            FieldMeta(
                name=attr_name,
                kind=_field_kind(field),
                operators=_field_ops(field),
                methods=_TAGS_METHODS if isinstance(field, TagsAccessor) else [],
                doc=_field_doc(attr_name, field),
            )
        )
    return NamespaceMeta(
        name=cls_name,
        doc=cls.__doc__ or "",
        fields=fields,
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@query_completions_router.get("/query_completions", response_model=QueryCompletionsResponse)
def get_query_completions() -> QueryCompletionsResponse:
    """Return completion metadata for the Monaco Python query editor.

    The response is derived by introspecting the live Python objects so the
    frontend autocomplete always reflects the real API.
    """
    namespaces = [
        _introspect_namespace(ImageSampleField, "ImageSampleField"),
    ]

    functions = [
        FunctionMeta(
            name="AND",
            signature="AND(*terms: MatchExpression) -> MatchExpression",
            doc=AND.__doc__ or "",
        ),
        FunctionMeta(
            name="OR",
            signature="OR(*terms: MatchExpression) -> MatchExpression",
            doc=OR.__doc__ or "",
        ),
        FunctionMeta(
            name="NOT",
            signature="NOT(term: MatchExpression) -> MatchExpression",
            doc=NOT.__doc__ or "",
        ),
    ]

    return QueryCompletionsResponse(namespaces=namespaces, functions=functions)
