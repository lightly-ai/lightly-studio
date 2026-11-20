from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import metadata_resolver
from tests.helpers_resolvers import create_collection, create_image


def test_get_by_sample_ids(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    image_a = create_image(session=db_session, collection_id=collection_id, file_path_abs="/a.png")
    image_b = create_image(session=db_session, collection_id=collection_id, file_path_abs="/b.png")
    image_c = create_image(session=db_session, collection_id=collection_id, file_path_abs="/c.png")
    metadata_resolver.bulk_update_metadata(
        session=db_session,
        sample_metadata=[(image_a.sample_id, {"key": "a"}), (image_b.sample_id, {"key": "b"})],
    )

    rows = metadata_resolver.get_by_sample_ids(
        session=db_session, sample_ids=[image_a.sample_id, image_b.sample_id, image_c.sample_id]
    )

    assert {(row.sample_id, row.data["key"]) for row in rows} == {
        (image_a.sample_id, "a"),
        (image_b.sample_id, "b"),
    }


def test_get_by_sample_ids__empty(db_session: Session) -> None:
    assert metadata_resolver.get_by_sample_ids(session=db_session, sample_ids=[]) == []
