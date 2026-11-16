"""Route that sets the extent of an object track on an MCAP sequence."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path
from pydantic import BaseModel

from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import NotFoundError
from lightly_studio.services import recording_service

extend_sequence_track_router = APIRouter()


class ExtendSequenceTrackInput(BaseModel):
    """The annotation source and the tick range the track should cover."""

    annotation_source_id: UUID
    start_seq_number: int
    end_seq_number: int


class ExtendSequenceTrackView(BaseModel):
    """The ticks that received a new, generated annotation."""

    created_seq_numbers: list[int]


@extend_sequence_track_router.post(
    "/tracks/{track_id}/extend", response_model=ExtendSequenceTrackView
)
def extend_sequence_track(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
    sequence_id: Annotated[UUID, Path(title="Sequence ID")],
    track_id: Annotated[UUID, Path(title="Object track ID")],
    body: ExtendSequenceTrackInput,
) -> ExtendSequenceTrackView:
    """Set the track to cover a tick range, deleting cuboids outside it.

    Raises:
        NotFoundError: If the sequence does not belong to the dataset.
    """
    created = recording_service.extend_sequence_track(
        session=session,
        dataset_id=dataset_id,
        sequence_id=sequence_id,
        track_id=track_id,
        annotation_source_id=body.annotation_source_id,
        start_seq_number=body.start_seq_number,
        end_seq_number=body.end_seq_number,
    )
    if created is None:
        raise NotFoundError(f"MCAP sequence {sequence_id} not found in dataset {dataset_id}.")
    return ExtendSequenceTrackView(created_seq_numbers=created)
