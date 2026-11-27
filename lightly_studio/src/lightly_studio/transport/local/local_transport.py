"""Transport that calls the resolvers in the same process."""

from __future__ import annotations

from lightly_studio.transport.export_transport import ExportTransport
from lightly_studio.transport.local.local_annotation_transport import LocalAnnotationTransport
from lightly_studio.transport.local.local_caption_transport import LocalCaptionTransport
from lightly_studio.transport.local.local_collection_transport import LocalCollectionTransport
from lightly_studio.transport.local.local_compute_transport import LocalComputeTransport
from lightly_studio.transport.local.local_ingestion_transport import LocalIngestionTransport
from lightly_studio.transport.local.local_metadata_transport import LocalMetadataTransport
from lightly_studio.transport.local.local_sample_transport import LocalSampleTransport
from lightly_studio.transport.local.local_tag_transport import LocalTagTransport


class LocalTransport:
    """Implements `StudioTransport` against the database of `db_manager`.

    Areas without a local implementation raise `AttributeError`, so `hasattr` is False.
    """

    def __init__(self) -> None:
        """Create the transports for each area."""
        self.annotations = LocalAnnotationTransport()
        self.collections = LocalCollectionTransport()
        self.samples = LocalSampleTransport()
        self.tags = LocalTagTransport()
        self.ingestion = LocalIngestionTransport()
        self.metadata = LocalMetadataTransport()
        self.captions = LocalCaptionTransport()
        self.compute = LocalComputeTransport()

    @property
    def export(self) -> ExportTransport:
        """The transport for export."""
        raise AttributeError("The local export transport does not exist yet.")
