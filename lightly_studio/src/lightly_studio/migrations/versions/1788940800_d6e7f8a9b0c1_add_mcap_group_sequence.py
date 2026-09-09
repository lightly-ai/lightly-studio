"""add mcap_group_sequence table.

Adds the optional 1:1 ``mcap_group_sequence`` specialisation on ``sequence``
(``sample_id`` PK/FK + ``mcap_path``). Sequences without this row stay valid.

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-09-09 12:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d6e7f8a9b0c1"
down_revision: str | Sequence[str] | None = "c5d6e7f8a9b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "mcap_group_sequence",
        sa.Column("mcap_path", sa.String(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["sample_id"],
            ["sequence.sample_id"],
        ),
        sa.PrimaryKeyConstraint("sample_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("mcap_group_sequence")
