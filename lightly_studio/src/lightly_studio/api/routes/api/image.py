"""This module contains the API routes for managing samples."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field

from lightly_studio.api.routes.api.collection import get_and_validate_collection_id
from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_NOT_FOUND,
)
from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.core.dataset_query.field import Field as DatasetQueryField
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.order_by import OrderByExpression, OrderByField
from lightly_studio.db_manager import SessionDep
from lightly_studio.errors import SortExprError
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.image import (
    ImageView,
    ImageViewsWithCount,
)
from lightly_studio.models.sort import SortDirection, SortFieldExpr, SortFieldSource, SortFieldSpec
from lightly_studio.resolvers import (
    image_resolver,
)
from lightly_studio.resolvers.image_filter import (
    ImageFilter,
)

image_router = APIRouter(tags=["image"])

_IMAGE_SORT_FIELDS: dict[str, DatasetQueryField] = {
    "file_name": ImageSampleField.file_name,
    "file_path_abs": ImageSampleField.file_path_abs,
    "created_at": ImageSampleField.created_at,
    "width": ImageSampleField.width,
    "height": ImageSampleField.height,
}

_SAMPLE_SORT_FIELDS: dict[str, DatasetQueryField] = {
    "created_at": ImageSampleField.created_at,
}


class ReadImagesRequest(BaseModel):
    """Request body for reading samples with text embedding."""

    filters: ImageFilter | None = Field(None, description="Filter parameters for samples")
    text_embedding: list[float] | None = Field(None, description="Text embedding to search for")
    sample_ids: list[UUID] | None = Field(None, description="The list of requested sample IDs")
    pagination: Paginated | None = Field(
        None, description="Pagination parameters for offset and limit"
    )
    sort_by: list[SortFieldExpr] | None = Field(None, description="Sort parameters for samples")


@image_router.get("/datasets/{dataset_id}/sort/image/fields")
def get_image_sort_fields(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset Id")],
) -> list[SortFieldSpec]:
    """Retrieve image fields available for sorting in a dataset."""
    return image_resolver.get_sort_field_specs(session=session, dataset_id=dataset_id)


@image_router.post("/collections/{collection_id}/images/list")
def read_images(
    session: SessionDep,
    collection_id: Annotated[UUID, Path(title="collection Id")],
    body: ReadImagesRequest,
) -> ImageViewsWithCount:
    """Retrieve a list of samples from the database with optional filtering.

    Args:
        session: The database session.
        collection_id: The ID of the collection to filter samples by.
        body: Optional request body containing text embedding.

    Returns:
        A list of filtered samples.
    """
    result = image_resolver.get_all_by_collection_id(
        session=session,
        collection_id=collection_id,
        pagination=body.pagination,
        filters=body.filters,
        text_embedding=body.text_embedding,
        sample_ids=body.sample_ids,
        order_by=_to_order_by_expressions(sort_by=body.sort_by),
    )
    # TODO(Michal, 10/2025): Add SampleView to ImageView and then use a response model
    # instead of manual conversion.
    scores: list[float | None] = (
        list(result.similarity_scores) if result.similarity_scores else [None] * len(result.samples)
    )
    return ImageViewsWithCount(
        samples=[
            ImageView.from_image_table(image=image, similarity_score=score)
            for image, score in zip(result.samples, scores)
        ],
        total_count=result.total_count,
        next_cursor=result.next_cursor,
    )


@image_router.get("/collections/{collection_id}/images/dimensions")
def get_image_dimensions(
    session: SessionDep,
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(get_and_validate_collection_id),
    ],
    annotation_label_ids: Annotated[list[UUID] | None, Query()] = None,
) -> dict[str, int]:
    """Get min and max dimensions of samples in a collection."""
    return image_resolver.get_dimension_bounds(
        session=session,
        collection_id=collection.collection_id,
        annotation_label_ids=annotation_label_ids,
    )


@image_router.get("/images/{sample_id}")
def read_image(
    session: SessionDep,
    sample_id: Annotated[UUID, Path(title="Sample Id")],
) -> ImageView:
    """Retrieve a single sample from the database."""
    image = image_resolver.get_by_id(session=session, sample_id=sample_id)
    if not image:
        raise HTTPException(status_code=HTTP_STATUS_NOT_FOUND, detail="Sample not found")

    return ImageView.from_image_table(image=image)


class SampleAdjacentsParams(BaseModel):
    """Parameters for getting adjacent samples."""

    filters: ImageFilter | None = None
    text_embedding: list[float] | None = None


class ReadImageSampleIdsRequest(BaseModel):
    """Request body for reading matching image sample ids."""

    filters: ImageFilter | None = Field(None, description="Filter parameters for images")


class ReadCountImageAnnotationsRequest(BaseModel):
    """Request body for reading image annotation counts."""

    filter: ImageFilter | None = None


@image_router.post("/collections/{collection_id}/images/sample_ids", response_model=list[UUID])
def get_image_sample_ids(
    session: SessionDep,
    collection_id: Annotated[UUID, Path(title="collection Id")],
    body: ReadImageSampleIdsRequest,
) -> list[UUID]:
    """Retrieve all sample ids of images matching the given filters."""
    return list(
        image_resolver.get_sample_ids(
            session=session,
            collection_id=collection_id,
            filters=body.filters,
        )
    )


@image_router.post("/collections/{collection_id}/images/annotations/count")
def count_image_annotations_by_collection(
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(get_and_validate_collection_id),
    ],
    session: SessionDep,
    body: ReadCountImageAnnotationsRequest | None = None,
) -> list[dict[str, str | int]]:
    """Get image annotation counts for a specific collection."""
    image_filter = body.filter if body and body.filter else None
    counts = image_resolver.count_image_annotations_by_collection(
        session=session,
        collection_id=collection.collection_id,
        image_filter=image_filter,
    )

    return [
        {
            "label_name": label_name,
            "current_count": current_count,
            "total_count": total_count,
        }
        for label_name, current_count, total_count in counts
    ]


def _to_order_by_expressions(
    sort_by: list[SortFieldExpr] | None,
) -> list[OrderByExpression] | None:
    """Translate API sort expressions to core order-by expressions."""
    if sort_by is None:
        return None
    return [_to_order_by_expression(sort_expr=sort_expr) for sort_expr in sort_by]


def _to_order_by_expression(sort_expr: SortFieldExpr) -> OrderByExpression:
    """Translate one API sort expression to a core order-by expression."""
    if sort_expr.aggregate_fn is not None:
        raise SortExprError(f"Unsupported image sort aggregate function: {sort_expr.aggregate_fn}")

    if sort_expr.source == SortFieldSource.IMAGE:
        order_by = OrderByField(_IMAGE_SORT_FIELDS[sort_expr.field_name])

        if sort_expr.direction is SortDirection.DESC:
            return order_by.desc()

        return order_by.asc()
    if sort_expr.source == SortFieldSource.SAMPLE:
        order_by = OrderByField(_SAMPLE_SORT_FIELDS[sort_expr.field_name])

        if sort_expr.direction is SortDirection.DESC:
            return order_by.desc()

        return order_by.asc()

    raise SortExprError(
            f"Unsupported source {sort_expr.source} for image sort field {sort_expr.field_name}"
        )
