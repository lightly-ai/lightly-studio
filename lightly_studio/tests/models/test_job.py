"""Tests for the Job model."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.job import JobStatus, JobTable, JobView

_RESOURCE_ID = UUID("00000000-0000-0000-0000-000000000001")


def test_job_table__defaults(db_session: Session) -> None:
    job = JobTable(job_type="export", resource_id=_RESOURCE_ID)
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    assert job.job_type == "export"
    assert job.resource_id == _RESOURCE_ID
    assert job.params == {}
    assert job.engine_run_id is None
    assert job.status == JobStatus.QUEUED
    assert job.progress == 0
    assert job.attempt == 0
    assert job.message is None
    assert job.created_at is not None
    assert job.started_at is None
    assert job.finished_at is None


def test_job_view__serialises_every_column() -> None:
    job = JobTable(
        job_id=UUID("00000000-0000-0000-0000-000000000002"),
        job_type="export",
        resource_id=_RESOURCE_ID,
        engine_run_id="run-1",
        status=JobStatus.FAILED,
        progress=40,
        attempt=2,
        message="Out of memory",
        params={"format": "coco"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        started_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        finished_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
    )

    view = JobView.model_validate(job).model_dump()

    assert view == {
        "job_id": UUID("00000000-0000-0000-0000-000000000002"),
        "job_type": "export",
        "resource_id": _RESOURCE_ID,
        "engine_run_id": "run-1",
        "status": JobStatus.FAILED,
        "progress": 40,
        "attempt": 2,
        "message": "Out of memory",
        "params": {"format": "coco"},
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "started_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
        "finished_at": datetime(2026, 1, 3, tzinfo=timezone.utc),
    }
