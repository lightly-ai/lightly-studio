from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from lightly_studio.models.sample_query import SampleInclude, SampleQueryRequest
from lightly_studio.transport.remote.http_sample_transport import HttpSampleTransport
from lightly_studio.transport.sample_transport import SampleTransport
from tests.helpers_resolvers import create_collection, create_image


class TestHttpSampleTransport:
    def test_get_by_ids(self, test_client: TestClient) -> None:
        transport: SampleTransport = HttpSampleTransport(client=test_client)

        with pytest.raises(NotImplementedError):
            transport.get_by_ids(sample_ids=[])

    def test_get_image_ids_by_paths(self, test_client: TestClient) -> None:
        transport: SampleTransport = HttpSampleTransport(client=test_client)

        with pytest.raises(NotImplementedError):
            transport.get_image_ids_by_paths(collection_id=uuid4(), file_paths=["/a.png"])

    def test_get_video_ids_by_stems(self, test_client: TestClient) -> None:
        transport: SampleTransport = HttpSampleTransport(client=test_client)

        with pytest.raises(NotImplementedError):
            transport.get_video_ids_by_stems(collection_id=uuid4())

    def test_query(self, test_client: TestClient, db_session: Session) -> None:
        collection_id = create_collection(session=db_session).collection_id
        for path in ["/a.png", "/b.png"]:
            create_image(session=db_session, collection_id=collection_id, file_path_abs=path)
        transport: SampleTransport = HttpSampleTransport(client=test_client)
        request = SampleQueryRequest(limit=1, include=[SampleInclude.TAGS])

        first = transport.query(collection_id=collection_id, request=request)
        second = transport.query(
            collection_id=collection_id,
            request=request.model_copy(update={"cursor": first.next_cursor}),
        )

        assert [s.file_name for s in first.samples + second.samples] == ["a.png", "b.png"]
        assert first.samples[0].tags == []
        assert second.next_cursor is None

    def test_query__bad_cursor(self, test_client: TestClient, db_session: Session) -> None:
        collection_id = create_collection(session=db_session).collection_id
        transport: SampleTransport = HttpSampleTransport(client=test_client)

        with pytest.raises(ValueError, match="not valid"):
            transport.query(collection_id=collection_id, request=SampleQueryRequest(cursor="x"))
