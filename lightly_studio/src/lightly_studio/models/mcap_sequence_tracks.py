"""API views for object track annotations in an MCAP sequence."""

from uuid import UUID

from pydantic import BaseModel


class TrackAnnotationView(BaseModel):
    """A tracked cuboid annotation at one sequence tick."""

    seq_number: int
    annotation_id: UUID
    annotation_source_id: UUID
    interpolated: bool


class SequenceTrackView(BaseModel):
    """A track's cuboid annotations from one annotation source."""

    object_track_id: UUID
    object_track_number: int
    annotation_source_id: UUID
    annotation_source_name: str
    annotation_label_name: str
    annotations: list[TrackAnnotationView]


class SequenceTrackListView(BaseModel):
    """Track annotations in one MCAP sequence."""

    tracks: list[SequenceTrackView]
