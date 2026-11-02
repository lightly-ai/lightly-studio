"""Write operations for workspace-managed object tracks."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel

from lightly_studio.api.routes.api.status import HTTP_STATUS_CONFLICT
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.models.annotation.object_track import ObjectTrackView
from lightly_studio.services.recording_service import edit_sequence_track
from lightly_studio.services.recording_service.edit_sequence_track import IntervalMode

edit_sequence_track_router = APIRouter()


class StartTrackInput(BaseModel):
    """Existing untracked cuboid to use as the first keyframe."""

    annotation_id: UUID


class ExtendTrackInput(BaseModel):
    """Existing cuboid at a later tick and the interval fill mode."""

    annotation_id: UUID
    mode: IntervalMode


@edit_sequence_track_router.post("/tracks", response_model=ObjectTrackView)
def start_track(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
    sequence_id: Annotated[UUID, Path(title="Sequence ID")],
    body: StartTrackInput,
) -> ObjectTrackView:
    """Start a managed track from a cuboid on the requested sequence."""
    try:
        track = edit_sequence_track.start_track(
            session=session,
            dataset_id=dataset_id,
            sequence_id=sequence_id,
            annotation_id=body.annotation_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=HTTP_STATUS_CONFLICT, detail=str(exc)) from exc
    return ObjectTrackView.model_validate(track)


@edit_sequence_track_router.post("/tracks/{track_id}/keyframes", response_model=ObjectTrackView)
def extend_track(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
    sequence_id: Annotated[UUID, Path(title="Sequence ID")],
    track_id: Annotated[UUID, Path(title="Track ID")],
    body: ExtendTrackInput,
) -> ObjectTrackView:
    """Attach a later cuboid as a keyframe and generate the interval."""
    try:
        track = edit_sequence_track.extend_track(
            session=session,
            dataset_id=dataset_id,
            sequence_id=sequence_id,
            track_id=track_id,
            annotation_id=body.annotation_id,
            mode=body.mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=HTTP_STATUS_CONFLICT, detail=str(exc)) from exc
    return ObjectTrackView.model_validate(track)
