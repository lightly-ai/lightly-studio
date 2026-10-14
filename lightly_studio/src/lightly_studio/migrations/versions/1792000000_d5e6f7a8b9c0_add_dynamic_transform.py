"""Add dynamic_transform.

Adds ``dynamic_transform`` (one row per ``/tf`` edge at one capture time, FK to
``recording.recording_id``). The same parent and child repeat as the pose changes.

Revision ID: d5e6f7a8b9c0
Revises: 8cb37a9d104e
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d5e6f7a8b9c0"
down_revision: str | Sequence[str] | None = "8cb37a9d104e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "dynamic_transform",
        sa.Column("parent", sa.String(), nullable=False),
        sa.Column("child", sa.String(), nullable=False),
        sa.Column("qx", sa.Float(), nullable=False),
        sa.Column("qy", sa.Float(), nullable=False),
        sa.Column("qz", sa.Float(), nullable=False),
        sa.Column("qw", sa.Float(), nullable=False),
        sa.Column("tx", sa.Float(), nullable=False),
        sa.Column("ty", sa.Float(), nullable=False),
        sa.Column("tz", sa.Float(), nullable=False),
        sa.Column("dynamic_transform_id", sa.Uuid(), nullable=False),
        sa.Column("timestamp_ns", sa.BigInteger(), nullable=False),
        sa.Column("recording_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["recording_id"],
            ["recording.recording_id"],
        ),
        sa.PrimaryKeyConstraint("dynamic_transform_id"),
    )
    op.create_index(
        "ix_dynamic_transform_recording_id_timestamp_ns",
        "dynamic_transform",
        ["recording_id", "timestamp_ns"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_dynamic_transform_recording_id_timestamp_ns",
        table_name="dynamic_transform",
    )
    op.drop_table("dynamic_transform")
