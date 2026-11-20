from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from lightly_studio.transport.ingestion_transport import IngestionTransport
from lightly_studio.transport.remote.http_ingestion_transport import HttpIngestionTransport


class TestHttpIngestionTransport:
    def test_add_images_from_path(self) -> None:
        with httpx.Client() as client:
            transport: IngestionTransport = HttpIngestionTransport(client=client)

            with pytest.raises(NotImplementedError):
                transport.add_images_from_path(
                    collection_id=uuid4(),
                    path="/images",
                    allowed_extensions=None,
                    embed=False,
                    tag_depth=0,
                    limit=None,
                )

    def test_add_images(self) -> None:
        with httpx.Client() as client:
            transport: IngestionTransport = HttpIngestionTransport(client=client)

            with pytest.raises(NotImplementedError):
                transport.add_images(collection_id=uuid4(), images=[])

    def test_add_directory_tags(self) -> None:
        with httpx.Client() as client:
            transport: IngestionTransport = HttpIngestionTransport(client=client)

            with pytest.raises(NotImplementedError):
                transport.add_directory_tags(
                    collection_id=uuid4(), path="/images", sample_ids=[], tag_depth=1
                )

    def test_embed_images(self) -> None:
        with httpx.Client() as client:
            transport: IngestionTransport = HttpIngestionTransport(client=client)

            with pytest.raises(NotImplementedError):
                transport.embed_images(collection_id=uuid4(), sample_ids=[])
