from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import export_job_resolver
from tests.helpers_resolvers import create_collection


def test_create(db_session: Session) -> None:
    collection = create_collection(session=db_session)

    job = export_job_resolver.create(
        session=db_session,
        collection_id=collection.collection_id,
        export_path="/exports/coco.json",
    )

    assert isinstance(job.export_key, UUID)
    assert job.collection_id == collection.collection_id
    assert job.export_path == "/exports/coco.json"
