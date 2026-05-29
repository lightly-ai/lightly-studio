"""Routes delivering 2D embeddings for visualization."""

from __future__ import annotations

import io
import json
from typing import Annotated
from uuid import UUID

import pyarrow as pa
from fastapi import APIRouter, Path, Response
from pyarrow import ipc
from pydantic import BaseModel, Field
from sqlmodel import select

from lightly_studio.api.routes.api.embedding_coloring import ColorBy, build_color_data
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.embedding_model import EmbeddingModelTable
from lightly_studio.resolvers import image_resolver, twodim_embedding_resolver, video_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter

embeddings2d_router = APIRouter()


class GetEmbeddings2DRequest(BaseModel):
    """Request body for retrieving 2D embeddings."""

    filters: ImageFilter | VideoFilter = Field(
        description="Filter parameters identifying matching samples"
    )
    color_by: ColorBy | None = None


@embeddings2d_router.post("/collections/{collection_id}/embeddings2d/default")
def get_2d_embeddings(
    session: SessionDep,
    collection_id: Annotated[UUID, Path(title="Collection Id")],
    body: GetEmbeddings2DRequest,
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
    )
    # TODO(Michal: 05/2026): Remove color_category when the frontend is updated.
    # `build_color_data` is filter-unaware and returns a list of color categories per sample.
    # Temporarily transform it back to a single category per sample.
    if color_by is not None:
        color_legend = {0: "Filtered out", 1: "Unassigned", **color_legend}
    primary_color_category = [
        _to_primary_color_category(color_categories=categories, fulfils_filter=fulfils)
        for categories, fulfils in zip(color_categories, fulfils_filter)
    ]

    schema = pa.schema(
        [
            pa.field("x", pa.float32()),
            pa.field("y", pa.float32()),
            pa.field("fulfils_filter", pa.uint8()),
            pa.field("color_category", pa.uint8()),
            pa.field("color_categories", pa.list_(pa.uint8())),
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
            "color_category": pa.array(primary_color_category, type=pa.uint8()),
            "color_categories": pa.array(color_categories, type=pa.list_(pa.uint8())),
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


def _to_primary_color_category(color_categories: list[int], fulfils_filter: int) -> int:
    """Pick the scalar color category for one sample.

    Reserves 0 for filtered-out samples and 1 for samples with no color category;
    otherwise returns the lowest color category.
    """
    if fulfils_filter == 0:
        return 0
    if not color_categories:
        return 1
    return color_categories[0]


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
