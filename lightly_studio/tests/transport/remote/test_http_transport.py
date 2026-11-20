from __future__ import annotations

import httpx
import pytest

from lightly_studio.transport.remote.http_annotation_transport import HttpAnnotationTransport
from lightly_studio.transport.remote.http_collection_transport import HttpCollectionTransport
from lightly_studio.transport.remote.http_sample_transport import HttpSampleTransport
from lightly_studio.transport.remote.http_tag_transport import HttpTagTransport
from lightly_studio.transport.remote.http_transport import HttpTransport
from lightly_studio.transport.studio_transport import StudioTransport


class TestHttpTransport:
    def test_areas(self) -> None:
        with httpx.Client() as client:
            transport: StudioTransport = HttpTransport(client=client)

            assert isinstance(transport.annotations, HttpAnnotationTransport)
            assert isinstance(transport.collections, HttpCollectionTransport)
            assert isinstance(transport.samples, HttpSampleTransport)
            assert isinstance(transport.tags, HttpTagTransport)

    @pytest.mark.parametrize("area", ["metadata", "ingestion", "compute", "export"])
    def test_area__not_implemented(self, area: str) -> None:
        with httpx.Client() as client, pytest.raises(AttributeError, match=r"does not exist yet"):
            getattr(HttpTransport(client=client), area)
