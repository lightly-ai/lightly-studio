"""Routes delivering 2D embeddings for visualization."""

from __future__ import annotations

import io
import json
from typing import Annotated
from uuid import UUID

import numpy as np
import pyarrow as pa
from fastapi import APIRouter, Depends, HTTPException, Path, Response

from pyarrow import ipc
from pydantic import BaseModel, Field

from lightly_studio.api.routes.api.embedding_coloring import ColorBy, build_color_data
from lightly_studio.api.routes.api.embedding_coloring import ColorBy, build_color_data
from lightly_studio.dataset.embedding_manager import (
    EmbeddingManager,
    EmbeddingManagerProvider,
    TextEmbedQuery,
)
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter
from lightly_studio.resolvers import (
    annotation_resolver,
    embedding_model_resolver,
    image_resolver,
    twodim_embedding_resolver,
    video_resolver,
)
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.models.embedding_model import EmbeddingModelTable
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.api.routes.api.status import HTTP_STATUS_BAD_REQUEST, HTTP_STATUS_NOT_FOUND
from lightly_studio.database.db_manager import SessionDep

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

    filters: ImageFilter | VideoFilter | AnnotationsFilter = Field(
        description="Filter parameters identifying matching samples"
    )
    color_by: ColorBy | None = None
    nlp_axes: NlpAxes | None = None
    pca_axes: PcaAxes | None = None
    reference_label_names: list[str] | None = None


@embeddings2d_router.post("/collections/{collection_id}/embeddings2d/default")
def get_2d_embeddings(
    session: SessionDep,
    collection_id: Annotated[UUID, Path(title="Collection Id")],
    body: GetEmbeddings2DRequest,
    embedding_manager: EmbeddingManagerDep,
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

    def _embed(text: str) -> list[float]:
        return embedding_manager.embed_text(
            collection_id=collection_id,
            text_query=TextEmbedQuery(
                text=text, embedding_model_id=embedding_model.embedding_model_id
            ),
        )

    label_marker_names = body.reference_label_names or []
    label_marker_embeddings = [_embed(name) for name in label_marker_names]

    reference_points: list[dict[str, object]] = []
    if body.nlp_axes is not None:
        direction_x, x_words = _project_text_axis(
            axis=body.nlp_axes.x,
            collection_id=collection_id,
            embedding_model_id=embedding_model.embedding_model_id,
            embedding_manager=embedding_manager,
        )
        direction_y, y_words = _project_text_axis(
            axis=body.nlp_axes.y,
            collection_id=collection_id,
            embedding_model_id=embedding_model.embedding_model_id,
            embedding_manager=embedding_manager,
        )
        # Axis markers: cartesian product of axis anchor words (e.g. "young male").
        axis_marker_labels = [f"{x_word} {y_word}" for x_word in x_words for y_word in y_words]
        axis_marker_embeddings = [_embed(label) for label in axis_marker_labels]
        # Pack axis + label markers into a single reference_embeddings list so the resolver
        # returns both sets of centroids in one pass.
        combined_embeddings = axis_marker_embeddings + label_marker_embeddings
        x_array, y_array, sample_ids, centroids = (
            twodim_embedding_resolver.get_twodim_embeddings_nlp(
                session=session,
                collection_id=collection_id,
                embedding_model_id=embedding_model.embedding_model_id,
                direction_x=direction_x,
                direction_y=direction_y,
                reference_embeddings=combined_embeddings,
            )
        )
        n_axis = len(axis_marker_labels)
        reference_points = [
            {"x": cx, "y": cy, "label": label, "kind": "axis"}
            for (cx, cy), label in zip(centroids[:n_axis], axis_marker_labels)
        ] + [
            {"x": cx, "y": cy, "label": label, "kind": "label"}
            for (cx, cy), label in zip(centroids[n_axis:], label_marker_names)
        ]
    elif body.pca_axes is not None and len(body.pca_axes.label_names) >= 2:  # noqa: PLR2004
        text_embeddings = [_embed(label_name) for label_name in body.pca_axes.label_names]
        x_array, y_array, sample_ids, centroids = (
            twodim_embedding_resolver.get_twodim_embeddings_pca(
                session=session,
                collection_id=collection_id,
                embedding_model_id=embedding_model.embedding_model_id,
                text_embeddings=text_embeddings,
                reference_embeddings=label_marker_embeddings,
            )
        )
        reference_points = [
            {"x": cx, "y": cy, "label": label, "kind": "label"}
            for (cx, cy), label in zip(centroids, label_marker_names)
        ]
    else:
        x_array, y_array, sample_ids, centroids = twodim_embedding_resolver.get_twodim_embeddings(
            session=session,
            collection_id=collection_id,
            embedding_model_id=embedding_model.embedding_model_id,
            reference_embeddings=label_marker_embeddings,
        )
        reference_points = [
            {"x": cx, "y": cy, "label": label, "kind": "label"}
            for (cx, cy), label in zip(centroids, label_marker_names)
        ]

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
            "reference_points": json.dumps(reference_points),
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


def _project_text_axis(
    axis: TextAxis,
    collection_id: UUID,
    embedding_model_id: UUID,
    embedding_manager: EmbeddingManager,
) -> tuple[list[float], list[str]]:
    """Embed a TextAxis and return its direction vector and its anchor words.

    The direction is ``embed(positive) - embed(negative)`` when a non-empty negative anchor
    is provided, otherwise just ``embed(positive)``. The returned word list has one entry
    for a single-anchor axis and two (negative, positive) for a contrastive axis — used to
    build reference-marker labels via the cartesian product of the two axes.
    """
    positive = np.asarray(
        embedding_manager.embed_text(
            collection_id=collection_id,
            text_query=TextEmbedQuery(text=axis.positive, embedding_model_id=embedding_model_id),
        )
    )
    negative_text = (axis.negative or "").strip()
    if not negative_text:
        direction = positive
        words = [axis.positive]
    else:
        negative = np.asarray(
            embedding_manager.embed_text(
                collection_id=collection_id,
                text_query=TextEmbedQuery(
                    text=negative_text, embedding_model_id=embedding_model_id
                ),
            )
        )
        direction = positive - negative
        words = [negative_text, axis.positive]
    return [float(v) for v in direction.tolist()], words


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
