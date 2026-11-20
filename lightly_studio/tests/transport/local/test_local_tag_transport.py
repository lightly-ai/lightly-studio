from __future__ import annotations

import pytest

from lightly_studio.database import db_manager
from lightly_studio.resolvers import tag_resolver
from lightly_studio.transport.local.local_tag_transport import LocalTagTransport
from lightly_studio.transport.tag_transport import TagTransport
from tests.helpers_resolvers import create_collection, create_image


@pytest.mark.usefixtures("patch_collection")
class TestLocalTagTransport:
    def test_get_by_name(self) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        transport: TagTransport = LocalTagTransport()
        transport.add_to_samples(collection_id=collection_id, tag_name="cat", sample_ids=[])

        tag = transport.get_by_name(collection_id=collection_id, tag_name="cat")

        assert tag is not None
        assert tag.name == "cat"
        assert transport.get_by_name(collection_id=collection_id, tag_name="dog") is None

    def test_get_names_by_sample_ids(self) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        image = create_image(session=session, collection_id=collection_id)
        untagged_image = create_image(
            session=session, collection_id=collection_id, file_path_abs="/untagged.png"
        )
        transport: TagTransport = LocalTagTransport()
        for tag_name in ["dog", "cat"]:
            transport.add_to_samples(
                collection_id=collection_id, tag_name=tag_name, sample_ids=[image.sample_id]
            )

        tag_names = transport.get_names_by_sample_ids(
            sample_ids=[image.sample_id, untagged_image.sample_id]
        )

        assert tag_names == {image.sample_id: ["cat", "dog"]}

    def test_add_to_samples(self) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        image = create_image(session=session, collection_id=collection_id)
        transport: TagTransport = LocalTagTransport()

        transport.add_to_samples(
            collection_id=collection_id, tag_name="cat", sample_ids=[image.sample_id]
        )

        tag_names = tag_resolver.get_names_by_sample_ids(
            session=session, sample_ids=[image.sample_id]
        )
        assert tag_names == {image.sample_id: ["cat"]}

    def test_remove_from_samples(self) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        image = create_image(session=session, collection_id=collection_id)
        transport: TagTransport = LocalTagTransport()
        transport.add_to_samples(
            collection_id=collection_id, tag_name="cat", sample_ids=[image.sample_id]
        )

        transport.remove_from_samples(
            collection_id=collection_id, tag_name="cat", sample_ids=[image.sample_id]
        )

        tag_names = tag_resolver.get_names_by_sample_ids(
            session=session, sample_ids=[image.sample_id]
        )
        assert tag_names == {}

    def test_remove_from_samples__tag_not_found(self) -> None:
        collection_id = create_collection(session=db_manager.persistent_session()).collection_id
        transport: TagTransport = LocalTagTransport()

        transport.remove_from_samples(collection_id=collection_id, tag_name="cat", sample_ids=[])

        assert transport.get_by_name(collection_id=collection_id, tag_name="cat") is None
