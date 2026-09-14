"""API routes for dataset recordings."""

from __future__ import annotations

from uuid import UUID

import fsspec
from fastapi import APIRouter

from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import NotFoundError
from lightly_studio.models.recording import RecordingTable, RecordingView
from lightly_studio.resolvers import recording_resolver

recording_router = APIRouter(tags=["recording"])


@recording_router.get("/recordings/{recording_id}", response_model=RecordingView)
def get_recording(session: SessionDep, recording_id: UUID) -> RecordingView:
    """Return recording metadata used to open an MCAP range session."""
    recording = recording_resolver.get_by_id(session=session, recording_id=recording_id)
    if recording is None:
        raise NotFoundError(f"Recording not found: {recording_id}")
    return _to_view(recording)


@recording_router.get("/datasets/{dataset_id}/recordings", response_model=list[RecordingView])
def get_dataset_recordings(session: SessionDep, dataset_id: UUID) -> list[RecordingView]:
    """Return recordings available to the dataset."""
    return [
        _to_view(recording)
        for recording in recording_resolver.get_all_by_dataset_id(
            session=session, dataset_id=dataset_id
        )
    ]


def _to_view(recording: RecordingTable) -> RecordingView:
    try:
        fs, fs_path = fsspec.core.url_to_fs(recording.uri)
        info = fs.info(fs_path)
    except FileNotFoundError as error:
        raise NotFoundError(f"Recording not found: {recording.uri}") from error
    etag = str(info.get("ETag") or info.get("etag") or info.get("mtime") or info["size"])
    return RecordingView(
        recording_id=recording.recording_id,
        dataset_id=recording.dataset_id,
        format=recording.format,
        uri=recording.uri,
        media_url=f"/mcap/media/recordings/{recording.recording_id}",
        size_bytes=int(info["size"]),
        etag=etag.strip('"'),
    )
