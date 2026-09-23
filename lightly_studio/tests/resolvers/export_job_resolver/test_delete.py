from __future__ import annotations

from uuid import uuid4

from sqlmodel import Session

from lightly_studio.resolvers import export_job_resolver
from tests.helpers_resolvers import create_collection


def test_delete(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    job = export_job_resolver.create(
        session=db_session,
        collection_id=collection.collection_id,
        export_path="/exports/coco.json",
    )

    deleted = export_job_resolver.delete(session=db_session, export_key=job.export_key)

    assert deleted is True
    assert export_job_resolver.get(session=db_session, export_key=job.export_key) is None


def test_delete__not_found__returns_false(db_session: Session) -> None:
    deleted = export_job_resolver.delete(session=db_session, export_key=uuid4())

    assert deleted is False
