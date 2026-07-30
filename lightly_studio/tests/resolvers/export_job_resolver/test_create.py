from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import export_job_resolver


def test_create(db_session: Session) -> None:
    job = export_job_resolver.create(
        session=db_session,
        export_path="/exports/coco.json",
    )

    assert isinstance(job.export_key, UUID)
    assert job.export_path == "/exports/coco.json"
