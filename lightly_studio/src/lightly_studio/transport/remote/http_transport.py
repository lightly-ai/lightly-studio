"""Transport that calls the v1 REST API of the Studio backend."""

from __future__ import annotations

import httpx

from lightly_studio.transport.annotation_transport import AnnotationTransport
from lightly_studio.transport.compute_transport import ComputeTransport
from lightly_studio.transport.export_transport import ExportTransport
from lightly_studio.transport.ingestion_transport import IngestionTransport
from lightly_studio.transport.metadata_transport import MetadataTransport
from lightly_studio.transport.remote.http_collection_transport import HttpCollectionTransport
from lightly_studio.transport.sample_transport import SampleTransport
from lightly_studio.transport.tag_transport import TagTransport


class HttpTransport:
    """Implements `StudioTransport` over HTTP.

    Areas without an HTTP implementation raise `AttributeError`, so `hasattr` is False.
    """

    def __init__(self, client: httpx.Client) -> None:
        """Create the transports for each area.

        Args:
            client: The HTTP client. Its base URL is the Studio backend, and it sends the
                authorization header.
        """
        self.collections = HttpCollectionTransport(client=client)

    @property
    def samples(self) -> SampleTransport:
        """The transport for samples."""
        raise AttributeError("The HTTP sample transport does not exist yet.")

    @property
    def tags(self) -> TagTransport:
        """The transport for tags."""
        raise AttributeError("The HTTP tag transport does not exist yet.")

    @property
    def metadata(self) -> MetadataTransport:
        """The transport for metadata and captions."""
        raise AttributeError("The HTTP metadata transport does not exist yet.")

    @property
    def annotations(self) -> AnnotationTransport:
        """The transport for annotations."""
        raise AttributeError("The HTTP annotation transport does not exist yet.")

    @property
    def ingestion(self) -> IngestionTransport:
        """The transport for ingestion."""
        raise AttributeError("The HTTP ingestion transport does not exist yet.")

    @property
    def compute(self) -> ComputeTransport:
        """The transport for compute."""
        raise AttributeError("The HTTP compute transport does not exist yet.")

    @property
    def export(self) -> ExportTransport:
        """The transport for export."""
        raise AttributeError("The HTTP export transport does not exist yet.")
