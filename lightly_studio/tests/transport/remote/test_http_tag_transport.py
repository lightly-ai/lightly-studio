from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.resolvers import tag_resolver
from lightly_studio.transport.remote import http_tag_transport
from lightly_studio.transport.remote.http_tag_transport import HttpTagTransport
from lightly_studio.transport.tag_transport import TagTransport
from tests.helpers_resolvers import create_collection, create_image


class TestHttpTagTransport:
    def test_get_by_name(self, test_client: TestClient, db_session: Session) -> None:
        collection_id = create_collection(session=db_session).collection_id
        transport: TagTransport = HttpTagTransport(client=test_client)
        transport.add_to_samples(collection_id=collection_id, tag_name="cat", sample_ids=[])

        tag = transport.get_by_name(collection_id=collection_id, tag_name="cat")

        assert tag is not None
        assert tag.name == "cat"
        assert transport.get_by_name(collection_id=collection_id, tag_name="dog") is None

    def test_get_names_by_sample_ids(self, test_client: TestClient) -> None:
        transport: TagTransport = HttpTagTransport(client=test_client)

        with pytest.raises(NotImplementedError):
            transport.get_names_by_sample_ids(sample_ids=[])

    def test_add_to_samples__remove_from_samples__in_batches(
        self, test_client: TestClient, db_session: Session, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(http_tag_transport, "MAX_SAMPLE_IDS_PER_REQUEST", 2)
        collection_id = create_collection(session=db_session).collection_id
        sample_ids = [
            create_image(
                session=db_session, collection_id=collection_id, file_path_abs=path
            ).sample_id
            for path in ["/a.png", "/b.png", "/c.png"]
        ]
        transport: TagTransport = HttpTagTransport(client=test_client)
        post_spy = mocker.spy(test_client, "post")

        transport.add_to_samples(collection_id=collection_id, tag_name="cat", sample_ids=sample_ids)
        added = tag_resolver.get_names_by_sample_ids(session=db_session, sample_ids=sample_ids)
        transport.remove_from_samples(
            collection_id=collection_id, tag_name="cat", sample_ids=sample_ids
        )
        removed = tag_resolver.get_names_by_sample_ids(session=db_session, sample_ids=sample_ids)

        assert added == {sample_id: ["cat"] for sample_id in sample_ids}
        assert removed == {}
        a, b, c = (str(sample_id) for sample_id in sample_ids)
        add_path = f"/api/v1/collections/{collection_id}/tags:add"
        remove_path = f"/api/v1/collections/{collection_id}/tags:remove"
        assert [
            (call.args[0], call.kwargs["json"]["sample_ids"]) for call in post_spy.call_args_list
        ] == [
            (add_path, [a, b]),
            (add_path, [c]),
            (remove_path, [a, b]),
            (remove_path, [c]),
        ]

    def test_split_samples(self, test_client: TestClient) -> None:
        transport: TagTransport = HttpTagTransport(client=test_client)

        with pytest.raises(NotImplementedError):
            transport.split_samples(
                collection_id=uuid4(), sample_ids=[], tag_sizes={"train": 1}, seed=None
            )
