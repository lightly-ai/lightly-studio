from __future__ import annotations

import pytest

from lightly_studio.transport.local.local_collection_transport import LocalCollectionTransport
from lightly_studio.transport.local.local_ingestion_transport import LocalIngestionTransport
from lightly_studio.transport.local.local_metadata_transport import LocalMetadataTransport
from lightly_studio.transport.local.local_sample_transport import LocalSampleTransport
from lightly_studio.transport.local.local_tag_transport import LocalTagTransport
from lightly_studio.transport.local.local_transport import LocalTransport


class TestLocalTransport:
    def test_areas(self) -> None:
        transport = LocalTransport()

        assert isinstance(transport.collections, LocalCollectionTransport)
        assert isinstance(transport.samples, LocalSampleTransport)
        assert isinstance(transport.tags, LocalTagTransport)
        assert isinstance(transport.ingestion, LocalIngestionTransport)
        assert isinstance(transport.metadata, LocalMetadataTransport)

    @pytest.mark.parametrize("area", ["annotations", "compute", "export"])
    def test_area__not_implemented(self, area: str) -> None:
        with pytest.raises(AttributeError, match=r"does not exist yet"):
            getattr(LocalTransport(), area)
        assert not hasattr(LocalTransport(), area)
