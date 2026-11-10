"""The transport that the Python API uses for all data access."""

from __future__ import annotations

from typing import Protocol

from lightly_studio.transport.collection_transport import CollectionTransport
from lightly_studio.transport.metadata_transport import MetadataTransport
from lightly_studio.transport.sample_transport import SampleTransport
from lightly_studio.transport.tag_transport import TagTransport


class StudioTransport(Protocol):
    """Groups the transports for each area of the Python API.

    `LocalTransport` runs in the same process as the database. An HTTP transport will call
    the Studio backend.
    """

    @property
    def collections(self) -> CollectionTransport:
        """The transport for collections."""

    @property
    def samples(self) -> SampleTransport:
        """The transport for samples."""

    @property
    def tags(self) -> TagTransport:
        """The transport for tags."""

    @property
    def metadata(self) -> MetadataTransport:
        """The transport for metadata and captions."""
