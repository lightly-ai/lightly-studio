"""Routes delivering 2D embeddings for visualization."""

from __future__ import annotations

import io
import json
from typing import Annotated
from uuid import UUID

import pyarrow as pa
from fastapi import APIRouter, HTTPException, Path, Response
from pyarrow import ipc
from pydantic import BaseModel, Field

from lightly_studio.api.routes.api.embedding_coloring import ColorBy, build_color_data
from lightly_studio.api.routes.api.status import HTTP_STATUS_BAD_REQUEST, HTTP_STATUS_NOT_FOUND
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.resolvers import (
    annotation_resolver,
    embedding_model_resolver,
    image_resolver,
    twodim_embedding_resolver,
    video_resolver,
)
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter

embeddings2d_router = APIRouter()


class GetEmbeddings2DRequest(BaseModel):
    """Request body for retrieving 2D embeddings."""

    filters: ImageFilter | VideoFilter | AnnotationsFilter = Field(
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
    collection = session.get(CollectionTable, collection_id)
    if collection is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Collection {collection_id} not found.",
        )
    _validate_filter_type(collection=collection, filters=body.filters)

    # TODO(Malte, 09/2025): Support choosing the embedding model via API parameter.
    embedding_model = embedding_model_resolver.get_default_by_collection_id(
        session=session,
        collection_id=collection_id,
    )
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
        matching_sample_ids=matching_sample_ids,
    )

    schema = pa.schema(
        [
            pa.field("x", pa.float32()),
            pa.field("y", pa.float32()),
            pa.field("fulfils_filter", pa.uint8()),
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


def _get_matching_sample_ids(
    session: SessionDep,
    collection_id: UUID,
    filters: ImageFilter | VideoFilter | AnnotationsFilter,
) -> set[UUID]:
    """Get the set of sample IDs that match the given filters.

    Args:
        session: Database session.
        collection_id: The ID of the collection to scope results to.
        filters: Filter object specifying the criteria.

    Returns:
        Set of sample IDs that match the filters.
    """
    if isinstance(filters, AnnotationsFilter):
        return set(
            annotation_resolver.get_sample_ids(
                session=session,
                collection_id=collection_id,
                filters=filters,
            )
        )
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


def _validate_filter_type(
    collection: CollectionTable,
    filters: ImageFilter | VideoFilter | AnnotationsFilter,
) -> None:
    if collection.sample_type == SampleType.IMAGE and isinstance(filters, ImageFilter):
        return
    if collection.sample_type == SampleType.VIDEO and isinstance(filters, VideoFilter):
        return
    if collection.sample_type == SampleType.ANNOTATION and isinstance(filters, AnnotationsFilter):
        return
    raise HTTPException(
        status_code=HTTP_STATUS_BAD_REQUEST,
        detail=f"Invalid filter type for {collection.sample_type.value} collection.",
    )
