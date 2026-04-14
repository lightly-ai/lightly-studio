"""Expose the available query fields and their supported operators.

This endpoint is the single source of truth that the frontend consumes to
build the filter UI.  Adding a new field to ``_FIELD_REGISTRY`` in
``core/dataset_query/wire.py`` and adding an entry to ``_FIELD_META`` below
is all that is needed to make a field available in the query builder.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from lightly_studio.core.dataset_query.field import (
    ComparableField,
    DatetimeField,
    OrdinalField,
)
from lightly_studio.core.dataset_query.wire import _FIELD_REGISTRY

query_fields_router = APIRouter()

# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

WireOp = Literal[">", ">=", "<", "<=", "==", "!="]
QueryFieldValueType = Literal["number", "text", "date"]

_ORDINAL_OPS: list[WireOp] = [">", ">=", "<", "<=", "==", "!="]
_COMPARABLE_OPS: list[WireOp] = ["==", "!="]


class QueryFieldSchema(BaseModel):
    """Schema for a single queryable field exposed to the frontend."""

    id: str
    """Short SVAR-friendly field ID used in the filter UI and DSL (e.g. ``"file_name"``)."""

    wire_name: str | None
    """Canonical wire-format field name sent to the backend (e.g. ``"image.file_name"``).
    ``None`` for special fields like ``"tag"`` that map to a different wire node type."""

    label: str
    """Human-readable display label shown in the filter builder."""

    type: QueryFieldValueType
    """Value type used by the frontend filter library to render the correct input."""

    operators: list[WireOp]
    """Operators supported by the backend for this field."""


class QueryFieldsResponse(BaseModel):
    """Response containing all fields available for filtering."""

    fields: list[QueryFieldSchema]


# ---------------------------------------------------------------------------
# Field metadata
# ---------------------------------------------------------------------------

# Maps wire_name → (short_id, display_label).
# Only fields listed here are exposed to the frontend; omitting a wire name
# hides it from the query builder (e.g. video fields are intentionally absent).
_FIELD_META: dict[str, tuple[str, str]] = {
    "image.file_name": ("file_name", "File Name"),
    "image.width": ("width", "Width (px)"),
    "image.height": ("height", "Height (px)"),
    "image.created_at": ("created_at", "Created At"),
}


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@query_fields_router.get("/query_fields", response_model=QueryFieldsResponse)
def get_query_fields() -> QueryFieldsResponse:
    """Return the fields and operators available for the query builder.

    The response is derived directly from ``_FIELD_REGISTRY`` and the field
    type hierarchy, so operator constraints are always in sync with what the
    backend actually accepts.
    """
    fields: list[QueryFieldSchema] = [
        # The tag field is special: it maps to a ``tags_contains`` wire node,
        # not a regular ``field`` node.  It is listed first so it appears at
        # the top of the field picker.
        QueryFieldSchema(
            id="tag",
            wire_name=None,
            label="Tag",
            type="text",
            operators=["==", "!="],
        )
    ]

    for wire_name, field_obj in _FIELD_REGISTRY.items():
        meta = _FIELD_META.get(wire_name)
        if meta is None:
            continue  # field not exposed in the frontend

        short_id, label = meta

        if isinstance(field_obj, DatetimeField):
            field_type: QueryFieldValueType = "date"
            ops = _ORDINAL_OPS
        elif isinstance(field_obj, OrdinalField):
            field_type = "number"
            ops = _ORDINAL_OPS
        elif isinstance(field_obj, ComparableField):
            field_type = "text"
            ops = _COMPARABLE_OPS
        else:
            continue

        fields.append(
            QueryFieldSchema(
                id=short_id,
                wire_name=wire_name,
                label=label,
                type=field_type,
                operators=ops,
            )
        )

    return QueryFieldsResponse(fields=fields)
