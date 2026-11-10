"""add schema_compat table.

One row that records the applied schema revision and the lowest client version
that can use it. The server writes the row after each upgrade.

Revision ID: 7b4e2f1b1a31
Revises: 8660d246e98e
Create Date: 2026-11-10 10:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7b4e2f1b1a31"
down_revision: str | Sequence[str] | None = "8660d246e98e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "schema_compat",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("oss_revision", sa.String(), nullable=False),
        sa.Column("min_client_version", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("schema_compat")
