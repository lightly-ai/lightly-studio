"""API routes for the query language DSL."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Path
from lark.exceptions import LarkError, UnexpectedCharacters, UnexpectedEOF, UnexpectedToken
from pydantic import BaseModel, Field
from sqlmodel import col, select

from lightly_studio.api.routes.api.collection import get_and_validate_collection_id
from lightly_studio.core.query_language import FieldRegistry, parse_query
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.tag import TagTable

query_language_router = APIRouter(tags=["query_language"])


# --- Request / response models ---


class ValidateRequest(BaseModel):
    """Request body for the validate endpoint."""

    text: str


class Diagnostic(BaseModel):
    """A single parse/validation diagnostic."""

    start: int
    end: int
    message: str
    severity: str = "error"


class ValidateResponse(BaseModel):
    """Response from the validate endpoint."""

    diagnostics: list[Diagnostic]


class SuggestRequest(BaseModel):
    """Request body for the suggest endpoint."""

    field: str
    prefix: str = ""
    limit: int = Field(20, gt=0, le=100)


class SuggestResponse(BaseModel):
    """Response from the suggest endpoint."""

    values: list[str]


# --- Helpers ---


def _lark_error_to_diagnostic(text: str, exc: LarkError) -> Diagnostic:
    """Convert a Lark parse error into a Diagnostic with character offsets."""
    if isinstance(exc, UnexpectedToken):
        token = exc.token
        start: int = getattr(token, "start_pos", None) or 0
        end = start + len(str(token))
        # TODO(Michal): Lark reports common EOF cases as UnexpectedToken with a
        # `$END` token for this grammar, so detect that explicitly and surface
        # "Unexpected end of input" instead of a generic token error.
        return Diagnostic(start=start, end=end, message=f"Unexpected token: {token!r}")
    if isinstance(exc, UnexpectedCharacters):
        # column is 1-based; for single-line input this equals the char offset
        start = exc.column - 1
        return Diagnostic(start=start, end=start + 1, message=f"Unexpected character: {exc.char!r}")
    if isinstance(exc, UnexpectedEOF):
        end_pos = len(text)
        return Diagnostic(start=end_pos, end=end_pos, message="Unexpected end of input")
    return Diagnostic(start=0, end=len(text), message=str(exc))


# --- Routes ---


@query_language_router.post("/collections/{collection_id}/query/validate")
def validate_query(
    collection_id: Annotated[UUID, Path(title="Collection ID")],  # noqa: ARG001
    body: ValidateRequest,
) -> ValidateResponse:
    """Validate query syntax and return diagnostics.

    Args:
        collection_id: The collection ID (unused; kept for consistent URL namespace).
        body: The query text to validate.

    Returns:
        A list of diagnostics (empty if valid).
    """
    try:
        registry = FieldRegistry()
        parse_query(body.text, registry)
        return ValidateResponse(diagnostics=[])
    except LarkError as exc:
        return ValidateResponse(diagnostics=[_lark_error_to_diagnostic(body.text, exc)])
    except ValueError as exc:
        return ValidateResponse(
            diagnostics=[Diagnostic(start=0, end=len(body.text), message=str(exc))]
        )


@query_language_router.get("/collections/{collection_id}/query-schema")
def get_query_schema(
    collection_id: Annotated[UUID, Path(title="Collection ID")],  # noqa: ARG001
) -> dict[str, Any]:
    """Return the field schema for the query language editor.

    Args:
        collection_id: The collection ID (unused; kept for consistent URL namespace).

    Returns:
        ``{"fields": [...], "subcontexts": {"annotation": [...]}}``
    """
    return FieldRegistry().get_schema()


@query_language_router.post("/collections/{collection_id}/query-suggest")
def suggest_values(
    session: SessionDep,
    collection: Annotated[
        CollectionTable,
        Depends(get_and_validate_collection_id),
    ],
    body: SuggestRequest,
) -> SuggestResponse:
    """Suggest field values for autocomplete.

    Args:
        session: Database session.
        collection: The validated collection (resolved via dependency).
        body: The field name, optional prefix, and result limit.

    Returns:
        Up to ``limit`` matching values.
    """
    prefix = f"{body.prefix.lower()}%"

    if body.field == "tags":
        rows = session.exec(
            select(TagTable.name)
            .where(TagTable.collection_id == collection.collection_id)
            .where(col(TagTable.name).ilike(prefix))
            .limit(body.limit)
        ).all()
        return SuggestResponse(values=list(rows))

    if body.field == "label":
        rows = session.exec(
            select(AnnotationLabelTable.annotation_label_name)
            .where(AnnotationLabelTable.dataset_id == collection.dataset_id)
            .where(col(AnnotationLabelTable.annotation_label_name).ilike(prefix))
            .limit(body.limit)
        ).all()
        return SuggestResponse(values=list(rows))

    return SuggestResponse(values=[])
