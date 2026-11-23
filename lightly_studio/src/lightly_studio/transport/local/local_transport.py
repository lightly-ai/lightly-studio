"""Transport that calls the resolvers in the same process."""

from __future__ import annotations

from lightly_studio.transport.annotation_transport import AnnotationTransport
from lightly_studio.transport.compute_transport import ComputeTransport
from lightly_studio.transport.export_transport import ExportTransport
from lightly_studio.transport.ingestion_transport import IngestionTransport
from lightly_studio.transport.local.local_collection_transport import LocalCollectionTransport
from lightly_studio.transport.local.local_metadata_transport import LocalMetadataTransport
from lightly_studio.transport.local.local_sample_transport import LocalSampleTransport
from lightly_studio.transport.local.local_tag_transport import LocalTagTransport


class LocalTransport:
    """Implements `StudioTransport` against the database of `db_manager`.

    Areas without a local implementation raise `AttributeError`, so `hasattr` is False.
    """

    def __init__(self) -> None:
        """Create the transports for each area."""
        self.collections = LocalCollectionTransport()
        self.samples = LocalSampleTransport()
        self.tags = LocalTagTransport()
        self.metadata = LocalMetadataTransport()

    @property
    def annotations(self) -> AnnotationTransport:
        """The transport for annotations."""
        raise AttributeError("The local annotation transport does not exist yet.")

    @property
    def ingestion(self) -> IngestionTransport:
        """The transport for ingestion."""
        raise AttributeError("The local ingestion transport does not exist yet.")

    @property
    def compute(self) -> ComputeTransport:
        """The transport for compute."""
        raise AttributeError("The local compute transport does not exist yet.")

    @property
    def export(self) -> ExportTransport:
        """The transport for export."""
        raise AttributeError("The local export transport does not exist yet.")
