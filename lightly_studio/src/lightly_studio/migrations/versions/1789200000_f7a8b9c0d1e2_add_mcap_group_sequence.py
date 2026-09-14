"""add mcap_group_sequence table.

Adds the optional 1:1 ``mcap_group_sequence`` specialisation on ``sequence``
(``sample_id`` PK/FK + ``recording_id`` FK to ``recording``). Sequences without this row
stay valid.

Revision ID: f7a8b9c0d1e2
Revises: 44741ab44511
Create Date: 2026-09-11 15:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7a8b9c0d1e2"
down_revision: str | Sequence[str] | None = "44741ab44511"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "mcap_group_sequence",
        sa.Column("recording_id", sa.Uuid(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["recording_id"],
            ["recording.recording_id"],
        ),
        sa.ForeignKeyConstraint(
            ["sample_id"],
            ["sequence.sample_id"],
        ),
        sa.PrimaryKeyConstraint("sample_id"),
    )
    op.create_index(
        op.f("ix_mcap_group_sequence_recording_id"),
        "mcap_group_sequence",
        ["recording_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_mcap_group_sequence_recording_id"), table_name="mcap_group_sequence")
    op.drop_table("mcap_group_sequence")
