from __future__ import annotations

from uuid import uuid4

from sqlmodel import Session

from lightly_studio.resolvers import export_job_resolver
from tests.helpers_resolvers import create_collection


def test_get(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    job = export_job_resolver.create(
        session=db_session,
        collection_id=collection.collection_id,
        export_path="/exports/coco_captions.json",
    )

    result = export_job_resolver.get(session=db_session, export_key=job.export_key)

    assert result is not None
    assert result.export_key == job.export_key
    assert result.export_path == "/exports/coco_captions.json"


def test_get__not_found(db_session: Session) -> None:
    result = export_job_resolver.get(session=db_session, export_key=uuid4())

    assert result is None
