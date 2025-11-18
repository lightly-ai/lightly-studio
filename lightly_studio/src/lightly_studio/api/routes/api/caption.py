"""API routes for dataset captions."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Path
from fastapi.params import Body
from pydantic import BaseModel
from typing_extensions import Annotated

from lightly_studio.db_manager import SessionDep
from lightly_studio.models.caption import CaptionCreate, CaptionTable, CaptionView
from lightly_studio.resolvers import caption_resolver


class CaptionCreateInput(BaseModel):
    """API interface to create caption."""

    parent_sample_id: UUID
    text: str = ""


captions_router = APIRouter(prefix="/datasets/{dataset_id}", tags=["captions"])


@captions_router.put("/captions/{caption_id}", response_model=CaptionView)
def update_caption_text(
    session: SessionDep,
    caption_id: Annotated[
        UUID,
        Path(title="Caption ID", description="ID of the caption to update"),
    ],
    text: Annotated[str, Body()],
) -> CaptionTable:
    """Update an existing caption in the database."""
    return caption_resolver.update_text(session=session, caption_id=caption_id, text=text)


@captions_router.get("/captions/{caption_id}", response_model=CaptionView)
def get_caption(
    session: SessionDep,
    caption_id: Annotated[UUID, Path(title="Caption ID")],
) -> CaptionTable:
    """Retrieve an existing annotation from the database."""
    captions = caption_resolver.get_by_ids(session, [caption_id])
    if not captions:
        raise ValueError(f"Caption with ID {caption_id} not found.")

    return captions[0]


@captions_router.post(
    "/captions",
    response_model=CaptionView,
)
def create_caption(
    dataset_id: Annotated[UUID, Path(title="Dataset Id", description="The ID of the dataset")],
    session: SessionDep,
    create_annotation_input: Annotated[CaptionCreateInput, Body()],
) -> CaptionTable:
    """Create a new caption."""
    input_caption = CaptionCreateInput(**create_annotation_input.model_dump())
    return caption_resolver.create_many(
        session=session,
        captions=[
            CaptionCreate(
                dataset_id=dataset_id,
                parent_sample_id=input_caption.parent_sample_id,
                text=input_caption.text,
            ),
        ],
    )[0]
