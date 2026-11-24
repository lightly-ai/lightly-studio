from __future__ import annotations

import pytest

from lightly_studio.database import db_manager
from lightly_studio.models.caption import CaptionCreate
from lightly_studio.resolvers import caption_resolver
from lightly_studio.transport.caption_transport import CaptionTransport
from lightly_studio.transport.local.local_caption_transport import LocalCaptionTransport
from tests.helpers_resolvers import create_collection, create_image


@pytest.mark.usefixtures("patch_collection")
class TestLocalCaptionTransport:
    def test_get(self) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        image_a = create_image(session=session, collection_id=collection_id, file_path_abs="/a")
        image_b = create_image(session=session, collection_id=collection_id, file_path_abs="/b")
        caption_resolver.create_many(
            session=session,
            parent_collection_id=collection_id,
            captions=[
                CaptionCreate(parent_sample_id=image_a.sample_id, text="a cat"),
                CaptionCreate(parent_sample_id=image_b.sample_id, text="a dog"),
            ],
        )
        transport: CaptionTransport = LocalCaptionTransport()

        captions = transport.get(parent_sample_ids=[image_a.sample_id])

        assert [(c.parent_sample_id, c.text) for c in captions] == [(image_a.sample_id, "a cat")]

    def test_add(self) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        image = create_image(session=session, collection_id=collection_id)
        transport: CaptionTransport = LocalCaptionTransport()

        caption_ids = transport.add(
            parent_collection_id=collection_id,
            captions=[CaptionCreate(parent_sample_id=image.sample_id, text="a cat")],
        )

        captions = transport.get(parent_sample_ids=[image.sample_id])
        assert [(c.sample_id, c.text) for c in captions] == [(caption_ids[0], "a cat")]

    def test_delete(self) -> None:
        session = db_manager.persistent_session()
        collection_id = create_collection(session=session).collection_id
        image = create_image(session=session, collection_id=collection_id)
        transport: CaptionTransport = LocalCaptionTransport()
        caption_ids = transport.add(
            parent_collection_id=collection_id,
            captions=[
                CaptionCreate(parent_sample_id=image.sample_id, text="a cat"),
                CaptionCreate(parent_sample_id=image.sample_id, text="a dog"),
            ],
        )

        transport.delete(caption_ids=[caption_ids[0]])

        captions = transport.get(parent_sample_ids=[image.sample_id])
        assert [c.text for c in captions] == ["a dog"]
