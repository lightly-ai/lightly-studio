"""Routes delivering 2D embeddings for visualization."""

from __future__ import annotations

import io
import json
from typing import Annotated
from uuid import UUID

import numpy as np
import pyarrow as pa
from fastapi import APIRouter, Depends, Path, Response
from pyarrow import ipc
from pydantic import BaseModel, Field
from sqlmodel import select

from lightly_studio.api.routes.api.embedding_coloring import ColorBy, build_color_data
from lightly_studio.dataset.embedding_manager import (
    EmbeddingManager,
    EmbeddingManagerProvider,
    TextEmbedQuery,
)
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.embedding_model import EmbeddingModelTable
from lightly_studio.resolvers import image_resolver, twodim_embedding_resolver, video_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter

embeddings2d_router = APIRouter()

EmbeddingManagerDep = Annotated[
    EmbeddingManager,
    Depends(lambda: EmbeddingManagerProvider.get_embedding_manager()),  # noqa: PLW0108
]


class TextAxis(BaseModel):
    """One natural-language axis with an optional contrastive negative anchor."""

    positive: str
    negative: str | None = None


class NlpAxes(BaseModel):
    """Prototype natural-language axes for LIG-9502 Variant A.

    Each axis is a TextAxis. If `negative` is provided, the axis direction is
    ``embed(positive) - embed(negative)`` (concept axis). Otherwise the direction is
    just ``embed(positive)``.
    """

    x: TextAxis
    y: TextAxis


class PcaAxes(BaseModel):
    """Prototype PCA-over-text axes for LIG-9502 Variant B."""

    label_names: list[str]


class GetEmbeddings2DRequest(BaseModel):
    """Request body for retrieving 2D embeddings."""

    filters: ImageFilter | VideoFilter = Field(
        description="Filter parameters identifying matching samples"
    )
    color_by: ColorBy | None = None
    nlp_axes: NlpAxes | None = None
    pca_axes: PcaAxes | None = None


@embeddings2d_router.post("/collections/{collection_id}/embeddings2d/default")
def get_2d_embeddings(
    session: SessionDep,
    collection_id: Annotated[UUID, Path(title="Collection Id")],
    body: GetEmbeddings2DRequest,
    embedding_manager: EmbeddingManagerDep,
) -> Response:
    """Return 2D embeddings serialized as an Arrow stream."""
    # TODO(Malte, 09/2025): Support choosing the embedding model via API parameter.
    embedding_model = session.exec(
        select(EmbeddingModelTable)
        .where(EmbeddingModelTable.collection_id == collection_id)
        .limit(1)
    ).first()
    if embedding_model is None:
        raise ValueError("No embedding model configured.")

    if body.nlp_axes is not None:
        direction_x = _build_text_axis_direction(
            axis=body.nlp_axes.x,
            collection_id=collection_id,
            embedding_model_id=embedding_model.embedding_model_id,
            embedding_manager=embedding_manager,
        )
        direction_y = _build_text_axis_direction(
            axis=body.nlp_axes.y,
            collection_id=collection_id,
            embedding_model_id=embedding_model.embedding_model_id,
            embedding_manager=embedding_manager,
        )
        x_array, y_array, sample_ids = twodim_embedding_resolver.get_twodim_embeddings_nlp(
            session=session,
            collection_id=collection_id,
            embedding_model_id=embedding_model.embedding_model_id,
            direction_x=direction_x,
            direction_y=direction_y,
        )
    elif body.pca_axes is not None and len(body.pca_axes.label_names) >= 2:  # noqa: PLR2004
        text_embeddings = [
            embedding_manager.embed_text(
                collection_id=collection_id,
                text_query=TextEmbedQuery(
                    text=label_name,
                    embedding_model_id=embedding_model.embedding_model_id,
                ),
            )
            for label_name in body.pca_axes.label_names
        ]
        x_array, y_array, sample_ids = twodim_embedding_resolver.get_twodim_embeddings_pca(
            session=session,
            collection_id=collection_id,
            embedding_model_id=embedding_model.embedding_model_id,
            text_embeddings=text_embeddings,
        )
    else:
        x_array, y_array, sample_ids = twodim_embedding_resolver.get_twodim_embeddings(
            session=session,
            collection_id=collection_id,
            embedding_model_id=embedding_model.embedding_model_id,
        )

    matching_sample_ids: set[UUID] | None = None
    filters = body.filters if body else None
    if filters:
        matching_sample_ids = _get_matching_sample_ids(
            session=session,
            collection_id=collection_id,
            filters=filters,
        )

    if matching_sample_ids is None:
        fulfils_filter = [1] * len(sample_ids)
    else:
        fulfils_filter = [1 if sample_id in matching_sample_ids else 0 for sample_id in sample_ids]

    color_by = body.color_by if body else None
    color_categories, color_legend = build_color_data(
        session=session,
        collection_id=collection_id,
        color_by=color_by,
        sample_ids=sample_ids,
        fulfils_filter=fulfils_filter,
    )

    schema = pa.schema(
        [
            pa.field("x", pa.float32()),
            pa.field("y", pa.float32()),
            pa.field("fulfils_filter", pa.uint8()),
            pa.field("color_category", pa.uint8()),
            pa.field("sample_id", pa.string()),
        ],
        metadata={
            "color_legend": json.dumps({str(k): v for k, v in color_legend.items()}),
        },
    )
    table = pa.table(
        {
            "x": pa.array(x_array, type=pa.float32()),
            "y": pa.array(y_array, type=pa.float32()),
            "fulfils_filter": pa.array(fulfils_filter, type=pa.uint8()),
            "color_category": pa.array(color_categories, type=pa.uint8()),
            "sample_id": pa.array([str(sample_id) for sample_id in sample_ids], type=pa.string()),
        },
        schema=schema,
    )

    buffer = io.BytesIO()
    with ipc.new_stream(buffer, table.schema) as writer:
        writer.write_table(table)
    buffer.seek(0)

    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.apache.arrow.stream",
        headers={
            "Content-Disposition": "inline; filename=embeddings2d.arrow",
            "Content-Type": "application/vnd.apache.arrow.stream",
            "X-Content-Type-Options": "nosniff",
        },
    )


def _build_text_axis_direction(
    axis: TextAxis,
    collection_id: UUID,
    embedding_model_id: UUID,
    embedding_manager: EmbeddingManager,
) -> list[float]:
    """Compute the axis direction vector for a TextAxis.

    Returns ``embed(positive) - embed(negative)`` if a non-empty negative anchor is
    provided; otherwise returns ``embed(positive)``.
    """
    positive = embedding_manager.embed_text(
        collection_id=collection_id,
        text_query=TextEmbedQuery(text=axis.positive, embedding_model_id=embedding_model_id),
    )
    negative_text = (axis.negative or "").strip()
    if not negative_text:
        return positive
    negative = embedding_manager.embed_text(
        collection_id=collection_id,
        text_query=TextEmbedQuery(text=negative_text, embedding_model_id=embedding_model_id),
    )
    return [float(value) for value in (np.asarray(positive) - np.asarray(negative)).tolist()]


def _get_matching_sample_ids(
    session: SessionDep,
    collection_id: UUID,
    filters: ImageFilter | VideoFilter,
) -> set[UUID]:
    """Get the set of sample IDs that match the given filters.

    Args:
        session: Database session.
        collection_id: The ID of the collection to scope results to.
        filters: Filter object specifying the criteria.

    Returns:
        Set of sample IDs that match the filters.
    """
    if isinstance(filters, VideoFilter):
        return video_resolver.get_sample_ids(
            session=session,
            collection_id=collection_id,
            filters=filters,
        )
    # Default to image_resolver for ImageFilter
    return image_resolver.get_sample_ids(
        session=session,
        collection_id=collection_id,
        filters=filters,
    )
