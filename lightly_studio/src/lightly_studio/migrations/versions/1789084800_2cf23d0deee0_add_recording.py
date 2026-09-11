"""add recording.

Adds the ``recording`` table (dataset-scoped sidecar). A row stores where the bytes of a
recorded bag file (e.g. an ``.mcap``) live (``uri``) and what format they are; no topic,
channel, calibration, or sequence link.

Revision ID: 2cf23d0deee0
Revises: d6e7f8a9b0c1
Create Date: 2026-09-11 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2cf23d0deee0"
down_revision: Union[str, Sequence[str], None] = "d6e7f8a9b0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "recording",
        sa.Column("format", sa.String(), nullable=False),
        sa.Column("uri", sa.String(), nullable=False),
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
