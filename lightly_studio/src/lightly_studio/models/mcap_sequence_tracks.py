"""Read-only track summaries for an MCAP sequence timeline."""

from uuid import UUID

from pydantic import BaseModel


class TrackAnnotationView(BaseModel):
    """A tracked cuboid at one sequence tick."""

    seq_number: int
    annotation_id: UUID
    interpolated: bool


class SequenceTrackView(BaseModel):
    """One track's annotations within the requested sequence."""

    object_track_id: UUID
    object_track_number: int
    annotations: list[TrackAnnotationView]


class SequenceTrackListView(BaseModel):
    """Tracks with cuboids in one MCAP sequence."""

    tracks: list[SequenceTrackView]
