"""add static_transform.

Adds ``static_transform`` (one row per ``/tf_static`` edge on a bag, FK to
``recording.recording_id`` only — TF edges are keyed by ROS frame name strings, not
``collection_id``s).

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-09-11 12:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8c9d0e1f2a3"
down_revision: str | Sequence[str] | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "static_transform",
        sa.Column("parent", sa.String(), nullable=False),
        sa.Column("child", sa.String(), nullable=False),
        sa.Column("qx", sa.Float(), nullable=False),
        sa.Column("qy", sa.Float(), nullable=False),
        sa.Column("qz", sa.Float(), nullable=False),
        sa.Column("qw", sa.Float(), nullable=False),
        sa.Column("tx", sa.Float(), nullable=False),
        sa.Column("ty", sa.Float(), nullable=False),
        sa.Column("tz", sa.Float(), nullable=False),
        sa.Column("static_transform_id", sa.Uuid(), nullable=False),
        sa.Column("recording_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["recording_id"],
            ["recording.recording_id"],
        ),
        sa.PrimaryKeyConstraint("static_transform_id"),
        sa.UniqueConstraint(
            "recording_id",
            "parent",
            "child",
            name="unique_static_transform_edge_per_recording",
        ),
    )
    op.create_index(
        op.f("ix_static_transform_recording_id"),
        "static_transform",
        ["recording_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_static_transform_recording_id"), table_name="static_transform")
    op.drop_table("static_transform")
