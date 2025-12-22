"""API routes for collection captions."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, Path
from pydantic import BaseModel
from typing_extensions import Annotated

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.caption import CaptionCreate, CaptionTable, CaptionView
from lightly_studio.resolvers import caption_resolver, sample_resolver


# TODO(jonas, 11/2025): Use CaptionCreate instead when CaptionTable is linked to SampleTable.
class CaptionCreateInput(BaseModel):
    """API interface to create caption."""

    parent_sample_id: UUID
    text: str = ""


captions_router = APIRouter(prefix="/collections/{collection_id}", tags=["captions"])


@captions_router.put("/captions/{sample_id}", response_model=CaptionView)
def update_caption_text(
    session: SessionDep,
    sample_id: Annotated[
        UUID,
        Path(title="Caption ID", description="ID of the caption to update"),
    ],
    text: Annotated[str, Body()],
) -> CaptionTable:
    """Update an existing caption in the database."""
    return caption_resolver.update_text(session=session, sample_id=sample_id, text=text)


@captions_router.get("/captions/{sample_id}", response_model=CaptionView)
def get_caption(
    session: SessionDep,
    sample_id: Annotated[UUID, Path(title="Caption ID")],
) -> CaptionTable:
    """Retrieve an existing annotation from the database."""
    captions = caption_resolver.get_by_ids(session, [sample_id])
    if not captions:
        raise ValueError(f"Caption with ID {sample_id} not found.")

    return captions[0]


@captions_router.post(
    "/captions",
    response_model=CaptionView,
)
def create_caption(
    session: SessionDep,
    create_caption_input: Annotated[CaptionCreateInput, Body()],
) -> CaptionTable:
    """Create a new caption."""
    # Get the parent sample
    parent_sample = sample_resolver.get_by_id(
        session=session, sample_id=create_caption_input.parent_sample_id
    )
    if parent_sample is None:
        raise ValueError(f"Sample with ID {create_caption_input.parent_sample_id} not found.")

    # Create the caption
    sample_ids = caption_resolver.create_many(
        session=session,
        parent_collection_id=parent_sample.collection_id,
        captions=[
            CaptionCreate(
                parent_sample_id=create_caption_input.parent_sample_id,
                text=create_caption_input.text,
            ),
        ],
    )
    assert len(sample_ids) == 1, "Expected exactly one caption to be created."

    # Fetch and return the created caption
    return caption_resolver.get_by_ids(session=session, sample_ids=sample_ids)[0]


@captions_router.delete("/captions/{sample_id}")
def delete_caption(
    session: SessionDep,
    sample_id: Annotated[UUID, Path(title="Caption ID", description="ID of the caption to delete")],
) -> dict[str, str]:
    """Delete a caption from the database."""
    try:
        caption_resolver.delete_caption(session=session, sample_id=sample_id)
    except ValueError as e:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail="Caption not found",
        ) from e
    return {"status": "deleted"}
