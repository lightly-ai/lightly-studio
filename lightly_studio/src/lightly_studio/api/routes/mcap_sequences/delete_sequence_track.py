"""Route that deletes an object track of an MCAP sequence."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Query
from pydantic import BaseModel

from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import NotFoundError
from lightly_studio.services import recording_service

delete_sequence_track_router = APIRouter()


class DeleteSequenceTrackView(BaseModel):
    """How many cuboids the deleted track had."""

    deleted_annotation_count: int


@delete_sequence_track_router.delete("/tracks/{track_id}", response_model=DeleteSequenceTrackView)
def delete_sequence_track(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
    sequence_id: Annotated[UUID, Path(title="Sequence ID")],
    track_id: Annotated[UUID, Path(title="Object track ID")],
    annotation_source_id: Annotated[UUID, Query(title="Annotation source ID")],
) -> DeleteSequenceTrackView:
    """Delete the track's cuboids in one annotation source, and the track once it is empty.

    Raises:
        NotFoundError: If the sequence does not belong to the dataset.
    """
    deleted = recording_service.delete_sequence_track(
        session=session,
        dataset_id=dataset_id,
        sequence_id=sequence_id,
        track_id=track_id,
        annotation_source_id=annotation_source_id,
    )
    if deleted is None:
        raise NotFoundError(f"MCAP sequence {sequence_id} not found in dataset {dataset_id}.")
    return DeleteSequenceTrackView(deleted_annotation_count=deleted)
