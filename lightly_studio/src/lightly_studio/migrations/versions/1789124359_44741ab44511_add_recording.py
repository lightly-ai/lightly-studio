"""add recording.

Adds the ``recording`` table (dataset-scoped sidecar) and the ``recordingformat`` enum. A row
stores where the bytes of a recorded bag file (e.g. an ``.mcap``) live (``uri``) and what format
they are; no topic, channel, calibration, or sequence link.

Revision ID: 44741ab44511
Revises: d6e7f8a9b0c1
Create Date: 2026-09-11 13:59:19.522487

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlmodel.sql.sqltypes import AutoString

# revision identifiers, used by Alembic.
revision: str = "44741ab44511"
down_revision: str | Sequence[str] | None = "d6e7f8a9b0c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
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
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["dataset.dataset_id"],
        ),
        sa.PrimaryKeyConstraint("recording_id"),
    )
    op.create_index(op.f("ix_recording_dataset_id"), "recording", ["dataset_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_recording_dataset_id"), table_name="recording")
    op.drop_table("recording")
    sa.Enum("MCAP", name="recordingformat").drop(op.get_bind())
