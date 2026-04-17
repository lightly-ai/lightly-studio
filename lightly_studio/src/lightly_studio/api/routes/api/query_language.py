"""API routes for the query language DSL."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Path
from lark.exceptions import LarkError, UnexpectedCharacters, UnexpectedEOF, UnexpectedToken
from pydantic import BaseModel, Field
from sqlmodel import col, func, select

from lightly_studio.api.routes.api.collection import get_and_validate_collection_id
from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.core.query_language import FieldRegistry, compile_ast, parse_to_ast
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.image import ImageTable, ImageView, ImageViewsWithCount
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.tag import TagTable
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.image_resolver.get_all_by_collection_id import (
    _compute_next_cursor,
    _get_load_options,
)
from lightly_studio.resolvers.similarity_utils import (
    apply_similarity_join,
    distance_to_similarity,
    get_distance_expression,
)

query_language_router = APIRouter(tags=["query_language"])


# --- Request / response models ---


class QueryRequest(BaseModel):
    """Request body for the query endpoint."""

    text: str
    filters: ImageFilter | None = Field(None, description="Filter parameters for samples")
    text_embedding: list[float] | None = Field(None, description="Text embedding to search for")
    sample_ids: list[UUID] | None = Field(None, description="The list of requested sample IDs")
    pagination: Paginated | None = Field(None)


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


@query_language_router.post("/collections/{collection_id}/images/query")
def query_images(
    session: SessionDep,
    collection: Annotated[
        CollectionTable,
        Path(title="Collection ID"),
        Depends(get_and_validate_collection_id),
    ],
    body: QueryRequest,
) -> ImageViewsWithCount:
    """Filter images in a collection using the query language DSL.

    Args:
        session: Database session.
        collection_id: The collection to query.
        body: Query text and optional pagination.

    Returns:
        Filtered images in the same shape as ``/images/list``.
    """
    registry = FieldRegistry()
    ast = parse_to_ast(body.text)
    condition = compile_ast(ast, registry).get()
    embedding_model_id, distance_expr = get_distance_expression(
        session=session,
        collection_id=collection.collection_id,
        text_embedding=body.text_embedding,
    )

    load_options = _get_load_options()

    if distance_expr is not None and embedding_model_id is not None:
        samples_query = (
            select(ImageTable, distance_expr)
            .options(load_options)
            .join(ImageTable.sample)
            .where(SampleTable.collection_id == collection.collection_id)
            .where(condition)
        )
        samples_query = apply_similarity_join(
            query=samples_query,
            sample_id_column=col(ImageTable.sample_id),
            embedding_model_id=embedding_model_id,
        )

        count_query = (
            select(func.count())
            .select_from(ImageTable)
            .join(ImageTable.sample)
            .where(SampleTable.collection_id == collection.collection_id)
            .where(condition)
        )
        count_query = apply_similarity_join(
            query=count_query,
            sample_id_column=col(ImageTable.sample_id),
            embedding_model_id=embedding_model_id,
        )
    else:
        samples_query = (
            select(ImageTable)
            .options(load_options)
            .join(ImageTable.sample)
            .where(SampleTable.collection_id == collection.collection_id)
            .where(condition)
        )
        count_query = (
            select(func.count())
            .select_from(ImageTable)
            .join(ImageTable.sample)
            .where(SampleTable.collection_id == collection.collection_id)
            .where(condition)
        )

    if body.filters:
        samples_query = body.filters.apply(samples_query)
        count_query = body.filters.apply(count_query)

    if body.sample_ids:
        samples_query = samples_query.where(col(ImageTable.sample_id).in_(body.sample_ids))
        count_query = count_query.where(col(ImageTable.sample_id).in_(body.sample_ids))

    if distance_expr is not None:
        samples_query = samples_query.order_by(distance_expr)
    else:
        samples_query = samples_query.order_by(col(ImageTable.file_path_abs).asc())

    if body.pagination is not None:
        samples_query = samples_query.offset(body.pagination.offset).limit(body.pagination.limit)

    total_count = session.exec(count_query).one()
    scores: list[float | None]
    if distance_expr is not None:
        results = session.exec(samples_query).all()
        samples = [result[0] for result in results]
        scores = [distance_to_similarity(result[1]) for result in results]
    else:
        samples = list(session.exec(samples_query).all())
        scores = [None] * len(samples)
    next_cursor = _compute_next_cursor(body.pagination, total_count)

    return ImageViewsWithCount(
        samples=[
            ImageView.from_image_table(image=image, similarity_score=score)
            for image, score in zip(samples, scores)
        ],
        total_count=total_count,
        next_cursor=next_cursor,
    )


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
        ast = parse_to_ast(body.text)
        # TODO(Michal): Also exercise `.get()` here so validation covers runtime
        # compiler failures that currently appear only in `/images/query`.
        compile_ast(ast, registry)
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
