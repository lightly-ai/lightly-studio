"""Read-only models of the labeling-workflow tables that Studio filters by.

The workflow service owns the `workflow` schema and its Alembic migrations. Studio adds no
migrations for these tables and only reads the columns below. The tables use their own
metadata, so `SQLModel.metadata.create_all()` and Studio's Alembic never see them.

The workflow service test `tests/migrations/test_studio_contract.py` fails if these columns
change. Change both places together.
"""

from __future__ import annotations

from enum import Enum
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import Column, MetaData, String, Table, Uuid


class WorkflowStatus(str, Enum):
    """A workflow status option of the dataset grid filter.

    Each option except `NOT_IN_WORKFLOW` is a batch file state. `NOT_IN_WORKFLOW` matches the
    samples that are in no batch of the dataset's project.
    """

    NOT_IN_WORKFLOW = "not_in_workflow"
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    REWORK = "rework"
    ACCEPTED = "accepted"


workflow_metadata = MetaData(schema="workflow")

project_table = Table(
    "project",
    workflow_metadata,
    Column("id", Uuid, primary_key=True),
    Column("dataset_id", Uuid, nullable=False),
)
"""A dataset's labeling project. A dataset has at most one project."""

batch_file_table = Table(
    "batch_file",
    workflow_metadata,
    Column("batch_id", Uuid, primary_key=True),
    Column("sample_id", Uuid, primary_key=True),
    Column("project_id", Uuid, nullable=False),
    Column("state", String, nullable=False),
    Column("labeler", String, nullable=True),
    Column("reviewer", String, nullable=True),
)
"""A sample in a batch, with the emails of its labeler and reviewer.

A sample is in at most one batch of a project.
"""


class SampleWorkflowView(BaseModel):
    """The batch of a sample in the dataset's workflow project, and the sample's state there."""

    project_id: UUID
    batch_id: UUID
    state: WorkflowStatus
