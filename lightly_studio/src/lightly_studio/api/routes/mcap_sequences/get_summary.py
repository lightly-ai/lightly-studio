"""Route to summarize the lidar and camera channels an indexed MCAP sequence has."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.models.mcap_sequence_summary import MCAPSequenceSummary
from lightly_studio.services.recording_service import get_mcap_sequence_summary

get_summary_router = APIRouter()


@get_summary_router.get("/summary", response_model=MCAPSequenceSummary)
def get_summary(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
    sequence_id: Annotated[UUID, Path(title="Sequence ID")],
) -> MCAPSequenceSummary:
    """Summarizes the lidar and camera channels available on an indexed MCAP sequence.

    Reads the channels straight out of the database: the component slots an indexing
    script attached to the sequence. Does not open the sequence's file, so the
    browser-based 3D labeling playground can initialize itself without waiting on a
    range request against the bag.

    Args:
        session: The database session.
        dataset_id: The dataset the sequence is expected to belong to.
        sequence_id: The MCAP sequence to summarize.

    Returns:
        The sequence's format and its channels, split into lidar (point cloud) and
        camera (image/video) channels.

    Raises:
        HTTPException: 404 if the sequence does not exist, does not belong to
            `dataset_id`, or has not been indexed yet.
    """
    summary = get_mcap_sequence_summary(
        session=session, dataset_id=dataset_id, sequence_id=sequence_id
    )
    if summary is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"MCAP sequence {sequence_id} not found in dataset {dataset_id}, or has not "
            "been indexed yet.",
        )
    return summary
