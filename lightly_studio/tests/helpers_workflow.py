"""Helpers for tests that read the workflow service's tables.

The workflow service owns these tables in production. Tests create them from Studio's
read-only models, on DuckDB and on Postgres.
"""

from __future__ import annotations

from collections.abc import Generator, Mapping
from contextlib import contextmanager
from uuid import UUID, uuid4

import sqlalchemy
from sqlmodel import Session

from lightly_studio.models import workflow


@contextmanager
def workflow_tables(session: Session) -> Generator[None, None, None]:
    """Create the workflow tables, and drop them on exit."""
    session.execute(sqlalchemy.text("CREATE SCHEMA IF NOT EXISTS workflow"))
    workflow.workflow_metadata.create_all(bind=session.connection())
    session.commit()
    try:
        yield
    finally:
        session.rollback()
        workflow.workflow_metadata.drop_all(bind=session.connection())
        session.execute(sqlalchemy.text("DROP SCHEMA IF EXISTS workflow"))
        session.commit()


def create_project(session: Session, dataset_id: UUID) -> UUID:
    """Insert a workflow project for a dataset and return its id."""
    project_id = uuid4()
    session.execute(
        sqlalchemy.insert(workflow.project_table).values(id=project_id, dataset_id=dataset_id)
    )
    session.commit()
    return project_id


def add_batch_files(session: Session, project_id: UUID, states: Mapping[UUID, str]) -> None:
    """Put samples in one batch of a project, each with its workflow state.

    Args:
        session: The database session.
        project_id: The project that holds the batch.
        states: The workflow state of each sample, by sample id.
    """
    batch_id = uuid4()
    session.execute(
        sqlalchemy.insert(workflow.batch_file_table),
        [
            {"batch_id": batch_id, "sample_id": sample_id, "project_id": project_id, "state": state}
            for sample_id, state in states.items()
        ],
    )
    session.commit()
