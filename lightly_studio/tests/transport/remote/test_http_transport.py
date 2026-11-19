from __future__ import annotations

import httpx
import pytest

from lightly_studio.transport.remote.http_collection_transport import HttpCollectionTransport
from lightly_studio.transport.remote.http_transport import HttpTransport
from lightly_studio.transport.studio_transport import StudioTransport


class TestHttpTransport:
    def test_collections(self) -> None:
        with httpx.Client() as client:
            transport: StudioTransport = HttpTransport(client=client)

            assert isinstance(transport.collections, HttpCollectionTransport)

    @pytest.mark.parametrize(
        "area", ["samples", "tags", "metadata", "annotations", "ingestion", "compute", "export"]
    )
    def test_area__not_implemented(self, area: str) -> None:
        with httpx.Client() as client, pytest.raises(AttributeError, match=r"does not exist yet"):
            getattr(HttpTransport(client=client), area)
