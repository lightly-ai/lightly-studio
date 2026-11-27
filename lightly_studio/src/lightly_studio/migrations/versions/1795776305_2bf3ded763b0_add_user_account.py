"""Add user_account.

Adds ``user_account``, one row per user id.

Revision ID: 2bf3ded763b0
Revises: 5d1c7e9a3b42
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2bf3ded763b0"
down_revision: str | Sequence[str] | None = "5d1c7e9a3b42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the user_account table."""
    op.create_table(
        "user_account",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    """Remove the user_account table."""
    op.drop_table("user_account")
