"""add sensor_calibration.

Adds ``sensor_calibration`` (one row per camera slot on a bag, FK to both
``recording.recording_id`` and ``mcap_group_component_definition.collection_id``).

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-09-10 12:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: str | Sequence[str] | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "sensor_calibration",
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("sensor_calibration_id", sa.Uuid(), nullable=False),
        sa.Column("recording_id", sa.Uuid(), nullable=False),
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("k", sa.ARRAY(sa.Float()), nullable=False),
        sa.ForeignKeyConstraint(
            ["recording_id"],
            ["recording.recording_id"],
        ),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["mcap_group_component_definition.collection_id"],
        ),
        sa.PrimaryKeyConstraint("sensor_calibration_id"),
        sa.UniqueConstraint(
            "recording_id",
            "collection_id",
            name="unique_sensor_calibration_slot_per_recording",
        ),
    )
    op.create_index(
        op.f("ix_sensor_calibration_recording_id"),
        "sensor_calibration",
        ["recording_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_sensor_calibration_recording_id"), table_name="sensor_calibration")
    op.drop_table("sensor_calibration")
