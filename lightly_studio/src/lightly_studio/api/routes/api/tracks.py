"""API routes for dataset object tracks."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path

from lightly_studio.database.db_manager import SessionDep
from lightly_studio.models.annotation.object_track import TrackWithClassNameView
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
