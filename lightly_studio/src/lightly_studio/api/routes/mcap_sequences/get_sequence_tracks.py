"""Route that returns tracked cuboids for an MCAP sequence."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Query

from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import NotFoundError
from lightly_studio.models.mcap_sequence_tracks import SequenceTrackListView
from lightly_studio.services import recording_service

get_sequence_tracks_router = APIRouter()


@get_sequence_tracks_router.get("/tracks", response_model=SequenceTrackListView)
def get_sequence_tracks(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
    sequence_id: Annotated[UUID, Path(title="Sequence ID")],
    annotation_source_id: Annotated[
        UUID | None,
        Query(description="Only return track annotations from this annotation source."),
    ] = None,
    target_frame_id: Annotated[
        str | None,
        Query(
            description=(
                "The coordinate frame the scene is shown in. Annotations at ticks whose "
                "cuboids cannot be mapped to this frame are left out."
            )
        ),
    ] = None,
) -> SequenceTrackListView:
    """Return tracked cuboid coverage for one sequence."""
    result = recording_service.get_sequence_tracks(
        session=session,
        dataset_id=dataset_id,
        sequence_id=sequence_id,
        annotation_source_id=annotation_source_id,
        target_frame_id=target_frame_id,
    )
    if result is None:
        raise NotFoundError(f"MCAP sequence {sequence_id} not found in dataset {dataset_id}.")
    return result
