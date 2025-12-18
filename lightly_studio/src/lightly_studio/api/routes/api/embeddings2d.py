"""Routes delivering 2D embeddings for visualization."""

from __future__ import annotations

import io
from uuid import UUID

import pyarrow as pa
from fastapi import APIRouter, Response
from pyarrow import ipc
from pydantic import BaseModel, Field
from sqlmodel import select

from lightly_studio.db_manager import SessionDep
from lightly_studio.models.embedding_model import EmbeddingModelTable
from lightly_studio.resolvers import image_resolver, twodim_embedding_resolver
from lightly_studio.resolvers.image_filter import ImageFilter

embeddings2d_router = APIRouter()


class GetEmbeddings2DRequest(BaseModel):
    """Request body for retrieving 2D embeddings."""

    filters: ImageFilter = Field(description="Filter parameters identifying matching samples")


@embeddings2d_router.post("/embeddings2d/default")
def get_2d_embeddings(
    session: SessionDep,
    body: GetEmbeddings2DRequest,
) -> Response:
    """Return 2D embeddings serialized as an Arrow stream."""
    collection_id = (
        body.filters.sample_filter.collection_id if body.filters.sample_filter is not None else None
    )
    if collection_id is None:
        raise ValueError("Collection ID must be provided in filters.")

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
        matching_samples_result = image_resolver.get_all_by_collection_id(
            session=session,
            collection_id=collection_id,
            filters=filters,
        )
        matching_sample_ids = {sample.sample_id for sample in matching_samples_result.samples}

    if matching_sample_ids is None:
        fulfils_filter = [1] * len(sample_ids)
    else:
        fulfils_filter = [1 if sample_id in matching_sample_ids else 0 for sample_id in sample_ids]

    table = pa.table(
        {
            "x": pa.array(x_array, type=pa.float32()),
            "y": pa.array(y_array, type=pa.float32()),
            "fulfils_filter": pa.array(fulfils_filter, type=pa.uint8()),
            "sample_id": pa.array([str(sample_id) for sample_id in sample_ids], type=pa.string()),
        }
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
