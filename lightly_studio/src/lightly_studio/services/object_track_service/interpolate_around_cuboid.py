"""Interpolate the ticks between a manual cuboid and the manual cuboids next to it."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.cuboid_interpolation import CuboidInterpolationRange
from lightly_studio.resolvers import annotation_resolver, object_track_resolver, sequence_resolver
from lightly_studio.services import object_track_service


def interpolate_around_cuboid(session: Session, annotation_id: UUID) -> None:
    """Interpolate a track from the previous to the next manual cuboid around a cuboid.

    Does nothing if the cuboid is not a manual cuboid of a track in a sequence.
    """
    annotation = annotation_resolver.get_by_id(session=session, annotation_id=annotation_id)
    if (
        annotation is None
        or annotation.object_track_id is None
        or annotation.cuboid_3d_details is None
        or annotation.cuboid_3d_details.interpolated
    ):
        return
    link = sequence_resolver.get_links_by_sample_ids(
        session=session, sample_ids={annotation.parent_sample_id}
    ).get(annotation.parent_sample_id)
    if link is None:
        return
    manual_seq_numbers = _manual_seq_numbers(
        session=session,
        object_track_id=annotation.object_track_id,
        annotation_source_id=annotation.annotation_collection_id,
        sequence_id=link.sequence_sample_id,
    )
    seq_number = link.seq_number
    start = max((n for n in manual_seq_numbers if n < seq_number), default=seq_number)
    end = min((n for n in manual_seq_numbers if n > seq_number), default=seq_number)
    if start == end:
        return
    track = object_track_resolver.get_by_id(
        session=session, object_track_id=annotation.object_track_id
    )
    if track is None:
        raise RuntimeError("Expected `track` to be set.")
    object_track_service.interpolate_cuboids(
        session=session,
        object_track=track,
        interpolation_range=CuboidInterpolationRange(
            sequence_id=link.sequence_sample_id,
            annotation_source_id=annotation.annotation_collection_id,
            start_seq_number=start,
            end_seq_number=end,
        ),
    )


def _manual_seq_numbers(
    session: Session, object_track_id: UUID, annotation_source_id: UUID, sequence_id: UUID
) -> set[int]:
    """Return the ticks of the track's manual cuboids of one source and sequence."""
    manual = [
        annotation
        for annotation in annotation_resolver.get_cuboids_by_object_track_ids(
            session=session, object_track_ids=[object_track_id]
        )
        if annotation.annotation_collection_id == annotation_source_id
        and annotation.cuboid_3d_details is not None
        and not annotation.cuboid_3d_details.interpolated
    ]
    links = sequence_resolver.get_links_by_sample_ids(
        session=session, sample_ids={annotation.parent_sample_id for annotation in manual}
    )
    return {link.seq_number for link in links.values() if link.sequence_sample_id == sequence_id}
