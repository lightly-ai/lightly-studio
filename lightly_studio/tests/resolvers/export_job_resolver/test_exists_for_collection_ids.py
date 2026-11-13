from __future__ import annotations

from sqlmodel import Session

from lightly_studio.resolvers import export_job_resolver
from tests.helpers_resolvers import create_collection


def test_exists_for_collection_ids(db_session: Session) -> None:
    exported = create_collection(session=db_session, collection_name="exported")
    other = create_collection(session=db_session, collection_name="other")
    export_job_resolver.create(
        session=db_session,
        collection_id=exported.collection_id,
        export_path="/exports/coco_captions.json",
    )

    assert export_job_resolver.exists_for_collection_ids(
        session=db_session, collection_ids=[other.collection_id, exported.collection_id]
    )
    assert not export_job_resolver.exists_for_collection_ids(
        session=db_session, collection_ids=[other.collection_id]
    )


def test_exists_for_collection_ids__no_ids(db_session: Session) -> None:
    exported = create_collection(session=db_session)
    export_job_resolver.create(
        session=db_session,
        collection_id=exported.collection_id,
        export_path="/exports/coco_captions.json",
    )

    assert not export_job_resolver.exists_for_collection_ids(session=db_session, collection_ids=[])
