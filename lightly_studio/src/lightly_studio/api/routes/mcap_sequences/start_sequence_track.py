"""Route that starts an object track from an existing cuboid of an MCAP sequence."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path
from pydantic import BaseModel

from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import NotFoundError
from lightly_studio.models.annotation.object_track import ObjectTrackView
from lightly_studio.services import recording_service

start_sequence_track_router = APIRouter()


class StartSequenceTrackInput(BaseModel):
    """The untracked cuboid that becomes the first annotation of the new track."""

    annotation_id: UUID


@start_sequence_track_router.post("/tracks", response_model=ObjectTrackView)
def start_sequence_track(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
    sequence_id: Annotated[UUID, Path(title="Sequence ID")],
    body: StartSequenceTrackInput,
) -> ObjectTrackView:
    """Create an object track from an untracked cuboid of the sequence.

    Raises:
        NotFoundError: If the sequence does not belong to the dataset.
    """
    track = recording_service.start_sequence_track(
        session=session,
        dataset_id=dataset_id,
        sequence_id=sequence_id,
        annotation_id=body.annotation_id,
    )
    if track is None:
        raise NotFoundError(f"MCAP sequence {sequence_id} not found in dataset {dataset_id}.")
    return ObjectTrackView.model_validate(track)
