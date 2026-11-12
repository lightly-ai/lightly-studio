"""API routes for MCAP sequences.

Each route handler is defined in its own module with its own ``APIRouter``. This
barrel aggregates them into a single ``mcap_sequences_router`` mounted by the
application.
"""

from __future__ import annotations

from fastapi import APIRouter

from lightly_studio.api.routes.mcap_sequences.delete_sequence_track import (
    delete_sequence_track_router,
)
from lightly_studio.api.routes.mcap_sequences.extend_sequence_track import (
    extend_sequence_track_router,
)
from lightly_studio.api.routes.mcap_sequences.get_sequence_tracks import get_sequence_tracks_router
from lightly_studio.api.routes.mcap_sequences.get_summary import get_summary_router
from lightly_studio.api.routes.mcap_sequences.get_tick_data import get_tick_data_router
from lightly_studio.api.routes.mcap_sequences.get_tick_details import get_tick_details_router
from lightly_studio.api.routes.mcap_sequences.get_ticks import get_ticks_router
from lightly_studio.api.routes.mcap_sequences.start_sequence_track import (
    start_sequence_track_router,
)

mcap_sequences_router = APIRouter(
    prefix="/datasets/{dataset_id}/mcap-sequences/{sequence_id}",
    tags=["mcap-sequences"],
)
mcap_sequences_router.include_router(get_summary_router)
mcap_sequences_router.include_router(get_ticks_router)
mcap_sequences_router.include_router(get_tick_details_router)
mcap_sequences_router.include_router(get_tick_data_router)
mcap_sequences_router.include_router(get_sequence_tracks_router)
mcap_sequences_router.include_router(start_sequence_track_router)
mcap_sequences_router.include_router(extend_sequence_track_router)
mcap_sequences_router.include_router(delete_sequence_track_router)

__all__ = ["mcap_sequences_router"]
