"""Transport that calls the resolvers in the same process."""

from __future__ import annotations

from lightly_studio.transport.local.local_collection_transport import LocalCollectionTransport
from lightly_studio.transport.metadata_transport import MetadataTransport
from lightly_studio.transport.sample_transport import SampleTransport
from lightly_studio.transport.tag_transport import TagTransport


class LocalTransport:
    """Implements `StudioTransport` against the database of `db_manager`.

    Areas without a local implementation raise `NotImplementedError`.
    """

    def __init__(self) -> None:
        """Create the transports for each area."""
        self.collections = LocalCollectionTransport()

    @property
    def samples(self) -> SampleTransport:
        """The transport for samples and captions."""
        raise NotImplementedError("The local sample transport does not exist yet.")

    @property
    def tags(self) -> TagTransport:
        """The transport for tags."""
        raise NotImplementedError("The local tag transport does not exist yet.")

    @property
    def metadata(self) -> MetadataTransport:
        """The transport for metadata."""
        raise NotImplementedError("The local metadata transport does not exist yet.")
