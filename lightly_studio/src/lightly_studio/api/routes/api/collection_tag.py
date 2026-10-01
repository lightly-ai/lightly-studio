"""This module contains the API routes for managing tags."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, StrictInt
from sqlalchemy.exc import IntegrityError
from sqlmodel import Field, select

from lightly_studio.api.routes.api.collection import get_and_validate_collection_id
from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_CONFLICT,
    HTTP_STATUS_CREATED,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_UNPROCESSABLE_ENTITY,
)
from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.tag import (
    TagCreate,
    TagCreateBody,
    TagRenameBody,
    TagTable,
    TagView,
)
from lightly_studio.resolvers import tag_resolver
from lightly_studio.resolvers.grid_filter import GridFilter
from lightly_studio.resolvers.grid_filter_sample_ids import build_sample_ids_query
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter

tag_router = APIRouter()


@tag_router.post(
    "/collections/{collection_id}/tags",
    response_model=TagView,
    status_code=HTTP_STATUS_CREATED,
)
def create_tag(
    session: SessionDep,
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(get_and_validate_collection_id),
    ],
    body: TagCreateBody,
) -> TagTable:
    """Create a new tag in the database."""
    collection_id = collection.collection_id
    try:
        return tag_resolver.create(
            session=session,
            tag=TagCreate(**body.model_dump(exclude_unset=True), collection_id=collection_id),
        )
    except IntegrityError as e:
        raise HTTPException(
            status_code=HTTP_STATUS_CONFLICT,
            detail=f"""
                Tag with name {body.name} already exists
                in the collection {collection_id}.
            """,
        ) from e


@tag_router.get("/collections/{collection_id}/tags", response_model=list[TagView])
def read_tags(
    session: SessionDep,
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(get_and_validate_collection_id),
    ],
    paginated: Annotated[Paginated, Query()],
) -> list[TagTable]:
    """Retrieve a list of tags from the database."""
    return tag_resolver.get_all_by_collection_id(
        session=session,
        collection_id=collection.collection_id,
        offset=paginated.offset,
        limit=paginated.limit,
    )


@tag_router.get("/collections/{collection_id}/tags/{tag_id}")
def read_tag(
    session: SessionDep,
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(get_and_validate_collection_id),
    ],
    tag_id: Annotated[UUID, Path(title="Tag Id")],
) -> TagTable:
    """Retrieve a single tag from the database."""
    tag = tag_resolver.get_by_id(session=session, tag_id=tag_id)
    if not tag:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"""
            Tag with id {tag_id} for collection {collection.collection_id} not found.
            """,
        )
    return tag


@tag_router.patch("/collections/{collection_id}/tags/{tag_id}", response_model=TagView)
def rename_tag(
    session: SessionDep,
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(get_and_validate_collection_id),
    ],
    tag_id: Annotated[UUID, Path(title="Tag Id")],
    body: TagRenameBody,
) -> TagTable:
    """Rename an existing tag."""
    try:
        tag = tag_resolver.rename(
            session=session,
            tag_id=tag_id,
            new_name=body.name,
        )
        if not tag:
            raise HTTPException(
                status_code=HTTP_STATUS_NOT_FOUND,
                detail=f"Tag with id {tag_id} not found.",
            )
    except IntegrityError as e:
        session.rollback()
        raise HTTPException(
            status_code=HTTP_STATUS_CONFLICT,
            detail=f"""
                Cannot rename tag. Tag with name {body.name}
                already exists in the collection {collection.collection_id}.
            """,
        ) from e
    return tag


@tag_router.delete("/collections/{collection_id}/tags/{tag_id}")
def delete_tag(
    session: SessionDep,
    # collection_id is needed for the generator
    collection_id: Annotated[  # noqa: ARG001
        UUID,
        Path(title="collection Id", description="The ID of the collection"),
    ],
    tag_id: Annotated[UUID, Path(title="Tag Id")],
) -> dict[str, str]:
    """Delete a tag from the database."""
    if not tag_resolver.delete(session=session, tag_id=tag_id):
        raise HTTPException(status_code=HTTP_STATUS_NOT_FOUND, detail="tag not found")
    return {"status": "deleted"}


class SampleIdsBody(BaseModel):
    """body parameters for adding or removing thing_ids."""

    sample_ids: list[UUID] | None = Field(None, description="sample ids to add/remove")


@tag_router.post(
    "/collections/{collection_id}/tags/{tag_id}/add/samples",
    status_code=HTTP_STATUS_CREATED,
)
def add_sample_ids_to_tag_id(
    session: SessionDep,
    # collection_id is needed for the generator
    collection_id: Annotated[
        UUID,
        Path(title="collection Id", description="The ID of the collection"),
    ],
    tag_id: UUID,
    body: SampleIdsBody,
) -> bool:
    """Add sample_ids to a tag_id."""
    tag = tag_resolver.get_by_id(session=session, tag_id=tag_id)
    if tag is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Tag {tag_id} not found, can't add sample_ids.",
        )
    # Validate the collection id.
    if tag.collection_id != collection_id:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Tag {tag_id} not found in collection {collection_id}.",
        )

    sample_ids = body.sample_ids if body.sample_ids else []
    tag_resolver.add_sample_ids_to_tag_id(session=session, tag_id=tag_id, sample_ids=sample_ids)
    return True


class TagByFilterBody(BaseModel):
    """Body for tagging every sample a grid filter matches.

    The caller must supply a filter to determine the sample type. The filter
    itself can have no conditions, e.g. ``{"filter_type": "image"}``.
    """

    filter: GridFilter


@tag_router.post(
    "/collections/{collection_id}/tags/{tag_id}/add/samples_by_filter",
    status_code=HTTP_STATUS_CREATED,
)
def add_samples_to_tag_by_filter(
    session: SessionDep,
    collection_id: Annotated[
        UUID,
        Path(title="collection Id", description="The ID of the collection"),
    ],
    tag_id: Annotated[UUID, Path(title="Tag Id")],
    body: TagByFilterBody,
) -> bool:
    """Tag every sample a grid filter matches.

    Idempotent on re-run.
    """
    tag = tag_resolver.get_by_id(session=session, tag_id=tag_id)
    if tag is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Tag {tag_id} not found, can't add samples.",
        )
    # Validate the collection id.
    if tag.collection_id != collection_id:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Tag {tag_id} not found in collection {collection_id}.",
        )

    sample_ids_query = build_sample_ids_query(
        session=session, collection_id=collection_id, grid_filter=body.filter
    )
    tag_resolver.add_samples_to_tag_from_query(
        session=session, tag_id=tag_id, sample_ids_query=sample_ids_query
    )
    return True


class SplitDefinitionBody(BaseModel):
    """One output tag and its relative size."""

    tag_name: str
    relative_size: StrictInt = Field(gt=0)


class SplitDatasetBody(BaseModel):
    """Body for splitting a grid-filtered image or video collection."""

    splits: list[SplitDefinitionBody] = Field(min_length=2)
    seed: int | None = None
    filter: GridFilter | None = None


class SplitDatasetResult(BaseModel):
    """A created tag and its assigned sample count."""

    tag_name: str
    sample_count: int


@tag_router.post(
    "/collections/{collection_id}/tags/split",
    response_model=list[SplitDatasetResult],
    status_code=HTTP_STATUS_CREATED,
)
def split_dataset(
    session: SessionDep,
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(get_and_validate_collection_id),
    ],
    body: SplitDatasetBody,
) -> list[SplitDatasetResult]:
    """Randomly partition matching image or video samples into new tags."""
    try:
        _validate_split_filter(collection=collection, grid_filter=body.filter)
        if body.filter is None:
            sample_ids = list(
                session.exec(
                    select(SampleTable.sample_id).where(
                        SampleTable.collection_id == collection.collection_id
                    )
                )
            )
        else:
            sample_ids = list(
                session.exec(
                    build_sample_ids_query(
                        session=session,
                        collection_id=collection.collection_id,
                        grid_filter=body.filter,
                    )
                )
            )
        counts = tag_resolver.split_samples(
            session=session,
            collection_id=collection.collection_id,
            sample_ids=sample_ids,
            splits=[
                tag_resolver.SplitDefinition(
                    tag_name=split.tag_name, relative_size=split.relative_size
                )
                for split in body.splits
            ],
            seed=body.seed,
        )
    except (ValueError, IntegrityError) as error:
        raise HTTPException(
            status_code=HTTP_STATUS_UNPROCESSABLE_ENTITY,
            detail="Invalid dataset split.",
        ) from error
    return [SplitDatasetResult(tag_name=name, sample_count=count) for name, count in counts.items()]


def _validate_split_filter(collection: CollectionTable, grid_filter: GridFilter | None) -> None:
    if collection.sample_type not in {SampleType.IMAGE, SampleType.VIDEO}:
        raise ValueError("Splitting is only supported for image and video collections.")
    if grid_filter is None:
        return
    expected_filter = ImageFilter if collection.sample_type == SampleType.IMAGE else VideoFilter
    if not isinstance(grid_filter, expected_filter):
        raise ValueError("The grid filter does not match the collection sample type.")


@tag_router.delete(
    "/collections/{collection_id}/tags/{tag_id}/remove/samples",
)
def remove_thing_ids_to_tag_id(
    session: SessionDep,
    tag_id: UUID,
    body: SampleIdsBody,
) -> bool:
    """Add thing_ids to a tag_id."""
    tag = tag_resolver.get_by_id(session=session, tag_id=tag_id)
    if not tag:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Tag {tag_id} not found, can't remove samples.",
        )

    sample_ids = body.sample_ids if body.sample_ids else []
    tag_resolver.remove_sample_ids_from_tag_id(
        session=session, tag_id=tag_id, sample_ids=sample_ids
    )
    return True
