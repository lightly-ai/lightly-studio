"""Tests for the Job model."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest
import sqlalchemy
from sqlmodel import Session, select

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


@pytest.mark.postgres_only  # The partial unique index only exists on Postgres.
@pytest.mark.parametrize("active_status", [JobStatus.QUEUED, JobStatus.RUNNING])
def test_job_table__second_active_job_rejected_by_database(
    db_session: Session, active_status: JobStatus
) -> None:
    db_session.add(JobTable(job_type="export", resource_id=_RESOURCE_ID, status=active_status))
    db_session.commit()

    db_session.add(JobTable(job_type="export", resource_id=_RESOURCE_ID))
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db_session.commit()
    # The failed commit leaves the session pending a rollback, without it the fixture
    # teardown fails when it commits the session.
    db_session.rollback()


@pytest.mark.postgres_only  # The partial unique index only exists on Postgres.
@pytest.mark.parametrize(
    "terminal_status", [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]
)
def test_job_table__new_job_allowed_after_terminal_job(
    db_session: Session, terminal_status: JobStatus
) -> None:
    db_session.add(JobTable(job_type="export", resource_id=_RESOURCE_ID, status=terminal_status))
    db_session.commit()

    db_session.add(JobTable(job_type="export", resource_id=_RESOURCE_ID))
    db_session.commit()

    jobs = db_session.exec(select(JobTable).where(JobTable.resource_id == _RESOURCE_ID)).all()
    assert sorted(job.status for job in jobs) == sorted([terminal_status, JobStatus.QUEUED])


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
