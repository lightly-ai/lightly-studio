"""Route for the tracks visible in one MCAP sequence."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path

from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import NotFoundError
from lightly_studio.models.mcap_sequence_tracks import SequenceTrackListView
from lightly_studio.services.recording_service import get_sequence_tracks

get_sequence_tracks_router = APIRouter()


@get_sequence_tracks_router.get("/tracks", response_model=SequenceTrackListView)
def get_tracks(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
    sequence_id: Annotated[UUID, Path(title="Sequence ID")],
) -> SequenceTrackListView:
    """Return track annotations for the sequence timeline."""
    result = get_sequence_tracks.get_sequence_tracks(
        session=session, dataset_id=dataset_id, sequence_id=sequence_id
    )
    if result is None:
        raise NotFoundError(f"MCAP sequence {sequence_id} not found in dataset {dataset_id}.")
    return result
