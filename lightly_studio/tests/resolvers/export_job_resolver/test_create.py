from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.export_job import ExportType
from lightly_studio.resolvers import export_job_resolver
from tests.helpers_resolvers import create_collection


def test_create(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    filter_json = {"export_format": "object_detection_coco", "annotation_collection_id": None}

    export_key = export_job_resolver.create(
        session=db_session,
        collection_id=collection.collection_id,
        export_type=ExportType.ANNOTATIONS,
        filter_json=filter_json,
    )

    assert isinstance(export_key, UUID)

    job = export_job_resolver.get(session=db_session, export_key=export_key)
    assert job is not None
    assert job.collection_id == collection.collection_id
    assert job.export_type == ExportType.ANNOTATIONS
    assert job.filter_json == filter_json
