"""API routes for dataset object tracks."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path

from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import NotFoundError
from lightly_studio.models.annotation.object_track import (
    ObjectTrackUpdate,
    TrackWithClassNameView,
)
from lightly_studio.resolvers import object_track_resolver

tracks_router = APIRouter(prefix="/datasets/{dataset_id}", tags=["tracks"])


@tracks_router.get(
    "/tracks",
    response_model=list[TrackWithClassNameView],
)
def get_tracks(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
) -> list[TrackWithClassNameView]:
    """Return all object tracks for a dataset with their annotation class names."""
    return object_track_resolver.get_all_with_class_name_by_dataset_id(
        session=session,
        dataset_id=dataset_id,
    )


@tracks_router.patch(
    "/tracks/{track_id}",
    response_model=TrackWithClassNameView,
)
def update_track(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
    track_id: Annotated[UUID, Path(title="Track ID")],
    body: ObjectTrackUpdate,
) -> TrackWithClassNameView:
    """Update an object track's parent relationship."""
    track = object_track_resolver.update_parent_track(
        session=session,
        dataset_id=dataset_id,
        object_track_id=track_id,
        parent_object_track_id=body.parent_object_track_id,
    )

    if track is None:
        raise NotFoundError(f"Track {track_id} not found.")

    # Re-fetch the enriched view so the response includes the class name.
    tracks = object_track_resolver.get_all_with_class_name_by_dataset_id(
        session=session,
        dataset_id=dataset_id,
    )
    return next(t for t in tracks if t.object_track_id == track.object_track_id)
