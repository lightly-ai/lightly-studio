"""Class for creating an mcap sample."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.create_sample import CreateSample
from lightly_studio.models.collection import SampleType
from lightly_studio.models.mcap import McapCreate
from lightly_studio.resolvers import mcap_resolver


@dataclass
class CreateMcap(CreateSample):
    """Class for creating an mcap sample.

    Stores a seek key into an ``.mcap`` file (channel id + log time, optionally a
    keyframe time for video), not pixels or point clouds. Decoding happens later from
    these fields.
    """

    channel_id: int
    """The MCAP channel id, unique within the source bag."""
    log_time_ns: int
    """The MCAP log time, in nanoseconds."""
    capture_timestamp_ns: int
    """The sensor/header capture timestamp, in nanoseconds."""
    keyframe_log_time_ns: int | None = None
    """Log time of the keyframe to seek to before decoding. Required for camera channels."""

    def create_in_collection(self, session: Session, collection_id: UUID) -> UUID:
        """Create an mcap sample in the specified collection.

        Args:
            session: Database session for resolver operations.
            collection_id: The ID of an MCAP collection to create the sample in.

        Returns:
            The UUID of the created mcap sample.
        """
        sample_ids = mcap_resolver.create_many(
            session=session,
            collection_id=collection_id,
            samples=[
                McapCreate(
                    channel_id=self.channel_id,
                    log_time_ns=self.log_time_ns,
                    capture_timestamp_ns=self.capture_timestamp_ns,
                    keyframe_log_time_ns=self.keyframe_log_time_ns,
                )
            ],
        )
        return sample_ids[0]

    def sample_type(self) -> SampleType:
        """Return the sample type."""
        return SampleType.MCAP
