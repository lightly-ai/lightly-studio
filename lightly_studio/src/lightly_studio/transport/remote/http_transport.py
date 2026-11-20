"""Transport that calls the v1 REST API of the Studio backend."""

from __future__ import annotations

import httpx

from lightly_studio.transport.compute_transport import ComputeTransport
from lightly_studio.transport.export_transport import ExportTransport
from lightly_studio.transport.metadata_transport import MetadataTransport
from lightly_studio.transport.remote.http_annotation_transport import HttpAnnotationTransport
from lightly_studio.transport.remote.http_collection_transport import HttpCollectionTransport
from lightly_studio.transport.remote.http_ingestion_transport import HttpIngestionTransport
from lightly_studio.transport.remote.http_sample_transport import HttpSampleTransport
from lightly_studio.transport.remote.http_tag_transport import HttpTagTransport


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
        self.annotations = HttpAnnotationTransport(client=client)
        self.collections = HttpCollectionTransport(client=client)
        self.samples = HttpSampleTransport(client=client)
        self.tags = HttpTagTransport(client=client)
        self.ingestion = HttpIngestionTransport(client=client)

    @property
    def metadata(self) -> MetadataTransport:
        """The transport for metadata and captions."""
        raise AttributeError("The HTTP metadata transport does not exist yet.")

    @property
    def compute(self) -> ComputeTransport:
        """The transport for compute."""
        raise AttributeError("The HTTP compute transport does not exist yet.")

    @property
    def export(self) -> ExportTransport:
        """The transport for export."""
        raise AttributeError("The HTTP export transport does not exist yet.")
