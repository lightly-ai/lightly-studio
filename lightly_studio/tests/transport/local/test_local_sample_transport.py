from __future__ import annotations

import pytest

from lightly_studio.database import db_manager
from lightly_studio.models.sample_query import SampleQueryRequest
from lightly_studio.transport.local.local_sample_transport import LocalSampleTransport
from lightly_studio.transport.sample_transport import SampleTransport
from tests.helpers_resolvers import create_collection, create_image


@pytest.mark.usefixtures("patch_collection")
class TestLocalSampleTransport:
    def test_get_by_ids(self) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        image = create_image(session=session, collection_id=collection_id)
        transport: SampleTransport = LocalSampleTransport()

        samples = transport.get_by_ids(sample_ids=[image.sample_id])

        assert [sample.sample_id for sample in samples] == [image.sample_id]

    def test_query(self) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        for path in ["/a.png", "/b.png"]:
            create_image(session=session, collection_id=collection_id, file_path_abs=path)
        transport: SampleTransport = LocalSampleTransport()

        page = transport.query(collection_id=collection_id, request=SampleQueryRequest(limit=1))
        next_page = transport.query(
            collection_id=collection_id,
            request=SampleQueryRequest(limit=1, cursor=page.next_cursor),
        )

        assert [sample.file_name for sample in page.samples] == ["a.png"]
        assert [sample.file_name for sample in next_page.samples] == ["b.png"]
        assert next_page.next_cursor is None

    def test_get_image_ids_by_paths(self) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        other_collection_id = create_collection(session=session).collection_id
        image = create_image(session=session, collection_id=collection_id, file_path_abs="/a.png")
        create_image(session=session, collection_id=other_collection_id, file_path_abs="/b.png")
        transport: SampleTransport = LocalSampleTransport()

        ids_by_path = transport.get_image_ids_by_paths(
            collection_id=collection_id, file_paths=["/a.png", "/b.png", "/c.png"]
        )

        assert ids_by_path == {"/a.png": image.sample_id}
