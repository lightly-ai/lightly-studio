from __future__ import annotations

from uuid import uuid4

from sqlmodel import Session

from lightly_studio.models.export_job import ExportType
from lightly_studio.resolvers import export_job_resolver
from tests.helpers_resolvers import create_collection


def test_get(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    export_key = export_job_resolver.create(
        session=db_session,
        collection_id=collection.collection_id,
        export_type=ExportType.CAPTIONS,
        filter_json={"image_filter": None},
    )

    result = export_job_resolver.get(session=db_session, export_key=export_key)

    assert result is not None
    assert result.export_key == export_key
    assert result.collection_id == collection.collection_id
    assert result.export_type == ExportType.CAPTIONS


def test_get__not_found(db_session: Session) -> None:
    result = export_job_resolver.get(session=db_session, export_key=uuid4())

    assert result is None
