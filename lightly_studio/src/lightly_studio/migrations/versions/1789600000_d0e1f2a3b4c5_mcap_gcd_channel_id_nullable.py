"""make mcap_group_component_definition.channel_id nullable.

The schema of an MCAP dataset is created before any recording is read, so the numeric
MCAP channel of a slot is unknown at that point. It is filled from the first recording
that is indexed.

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-09-17 10:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d0e1f2a3b4c5"
down_revision: str | Sequence[str] | None = "c9d0e1f2a3b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "mcap_group_component_definition",
        "channel_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(sa.text("DELETE FROM mcap_group_component_definition WHERE channel_id IS NULL"))
    op.alter_column(
        "mcap_group_component_definition",
        "channel_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
