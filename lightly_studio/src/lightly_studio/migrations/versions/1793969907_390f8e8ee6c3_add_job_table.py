"""add_job_table.

Adds the `job` table and the `jobstatus` enum. The partial unique index
`uq_job_resource_active` on `job(resource_id) WHERE status IN ('QUEUED', 'RUNNING')` makes
sure that a resource has at most one active job. The `WHERE` clause uses the enum names,
because SQLAlchemy stores the names of `JobStatus` members, not their values.

The index is declared here only and not on `JobTable`: DuckDB cannot create partial
indexes, and jobs are PostgreSQL-only. `_include_object` in `migrations/env.py` keeps
autogenerate from dropping the index.

Revision ID: 390f8e8ee6c3
Revises: 8660d246e98e
Create Date: 2026-11-06 14:58:27.677211

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlmodel.sql.sqltypes import AutoString

# revision identifiers, used by Alembic.
revision: str = "390f8e8ee6c3"
down_revision: Union[str, Sequence[str], None] = "8660d246e98e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STATUSES = ("QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED")
_ACTIVE_INDEX_NAME = "uq_job_resource_active"


def upgrade() -> None:
    """Upgrade schema."""
    sa.Enum(*_STATUSES, name="jobstatus").create(op.get_bind())
    op.create_table(
        "job",
        sa.Column("job_type", AutoString(), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column(
            "params",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("engine_run_id", AutoString(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(*_STATUSES, name="jobstatus", create_type=False),
            nullable=False,
        ),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("message", AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("job_id"),
    )
    op.create_index(op.f("ix_job_resource_id"), "job", ["resource_id"], unique=False)
    op.create_index(
        _ACTIVE_INDEX_NAME,
        "job",
        ["resource_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('QUEUED', 'RUNNING')"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(_ACTIVE_INDEX_NAME, table_name="job")
    op.drop_index(op.f("ix_job_resource_id"), table_name="job")
    op.drop_table("job")
    sa.Enum(*_STATUSES, name="jobstatus").drop(op.get_bind())
