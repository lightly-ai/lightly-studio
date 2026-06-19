"""This module contains the API routes for managing tags."""

from __future__ import annotations

from typing import Annotated, Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel
from pydantic import Field as PydanticField
from sqlalchemy.exc import IntegrityError
from sqlmodel import Field
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.api.routes.api.collection import get_and_validate_collection_id
from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_CONFLICT,
    HTTP_STATUS_CREATED,
    HTTP_STATUS_NOT_FOUND,
)
from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.tag import (
    TagCreate,
    TagCreateBody,
    TagKind,
    TagRenameBody,
    TagTable,
    TagView,
)
from lightly_studio.resolvers import (
    annotation_resolver,
    image_resolver,
    tag_resolver,
    video_frame_resolver,
    video_resolver,
)
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter
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
    collection_id: Annotated[  # noqa: ARG001
        UUID,
        Path(title="collection Id", description="The ID of the collection"),
    ],
    tag_id: UUID,
    body: SampleIdsBody,
) -> bool:
    """Add sample_ids to a tag_id."""
    # TODO(LIG-9942): backfill the collection-scope and tag-kind validation that
    # add_samples_to_tag_by_filter enforces (separate PR — see plan, out of scope here).
    tag = tag_resolver.get_by_id(session=session, tag_id=tag_id)
    if not tag:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Tag {tag_id} not found, can't add sample_ids.",
        )

    sample_ids = body.sample_ids if body.sample_ids else []
    tag_resolver.add_sample_ids_to_tag_id(session=session, tag_id=tag_id, sample_ids=sample_ids)
    return True


# A grid filter is self-describing: its ``filter_type`` literal selects both the source
# table to tag from and the tag kind it is allowed to write. Mirrors the discriminated
# union in ``services/sample_services/sample_adjacents_service.py``.
GridFilter = Annotated[
    Union[ImageFilter, VideoFilter, VideoFrameFilter, AnnotationsFilter],
    PydanticField(discriminator="filter_type"),
]


class TagByFilterBody(BaseModel):
    """Body for tagging every sample a grid filter matches.

    ``filter`` is required, not optional: the source table is dispatched on
    ``filter.filter_type``, so a ``null`` filter would be ambiguous. "Whole
    collection" is expressed as a typed-but-empty filter (e.g. ``{"filter_type":
    "image"}`` with no constraints), which the frontend already produces per grid.
    """

    filter: GridFilter


def _build_sample_ids_query(
    grid_filter: ImageFilter | VideoFilter | VideoFrameFilter | AnnotationsFilter,
    collection_id: UUID,
) -> SelectOfScalar[UUID]:
    """Dispatch a grid filter to its resolver's ``build_sample_ids_query``.

    The 4-branch dispatch mirrors the frontend's ``useSelectAll.fetchSampleIds``
    switch; each branch scopes to ``collection_id`` and applies the filter.
    """
    if isinstance(grid_filter, ImageFilter):
        return image_resolver.build_sample_ids_query(
            collection_id=collection_id, filters=grid_filter
        )
    if isinstance(grid_filter, VideoFilter):
        return video_resolver.build_sample_ids_query(
            collection_id=collection_id, filters=grid_filter
        )
    if isinstance(grid_filter, VideoFrameFilter):
        return video_frame_resolver.build_sample_ids_query(
            collection_id=collection_id, filters=grid_filter
        )
    return annotation_resolver.build_sample_ids_query(
        collection_id=collection_id, filters=grid_filter
    )


def _expected_tag_kind(
    grid_filter: ImageFilter | VideoFilter | VideoFrameFilter | AnnotationsFilter,
) -> TagKind:
    """Return the tag kind a grid may write: annotations grid ⇒ annotation, else sample."""
    return "annotation" if isinstance(grid_filter, AnnotationsFilter) else "sample"


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
    """Tag every sample a grid filter matches, entirely inside the DB.

    No sample ids cross the wire: the matched ids are inserted via a single
    server-side ``INSERT … SELECT``. Idempotent on re-run.
    """
    tag = tag_resolver.get_by_id(session=session, tag_id=tag_id)
    if not tag:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Tag {tag_id} not found, can't add samples.",
        )
    # The link table carries only sample/tag FKs, so neither the collection scope nor
    # the tag kind is enforced by the schema; both must be checked here.
    if tag.collection_id != collection_id:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Tag {tag_id} not found in collection {collection_id}.",
        )
    expected_kind = _expected_tag_kind(body.filter)
    if tag.kind != expected_kind:
        raise HTTPException(
            status_code=HTTP_STATUS_BAD_REQUEST,
            detail=(
                f"Tag {tag_id} has kind '{tag.kind}', but the "
                f"'{body.filter.filter_type}' grid requires kind '{expected_kind}'."
            ),
        )

    sample_ids_query = _build_sample_ids_query(grid_filter=body.filter, collection_id=collection_id)
    tag_resolver.add_samples_to_tag_from_query(
        session=session, tag_id=tag_id, sample_ids_query=sample_ids_query
    )
    return True


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
