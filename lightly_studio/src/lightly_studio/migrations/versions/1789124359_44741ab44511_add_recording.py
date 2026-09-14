"""Add dataset-scoped recordings."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlmodel.sql.sqltypes import AutoString

revision: str = "44741ab44511"
down_revision: str | Sequence[str] | None = "c5d6e7f8a9b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the recording table."""
    sa.Enum("MCAP", name="recordingformat").create(op.get_bind())
    op.create_table(
        "recording",
        sa.Column(
            "format",
            postgresql.ENUM("MCAP", name="recordingformat", create_type=False),
            nullable=False,
        ),
        sa.Column("uri", AutoString(), nullable=False),
        sa.Column("recording_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["dataset.dataset_id"]),
        sa.PrimaryKeyConstraint("recording_id"),
    )
    op.create_index("ix_recording_dataset_id", "recording", ["dataset_id"])


def downgrade() -> None:
    """Drop the recording table."""
    op.drop_index("ix_recording_dataset_id", table_name="recording")
    op.drop_table("recording")
    sa.Enum("MCAP", name="recordingformat").drop(op.get_bind())
