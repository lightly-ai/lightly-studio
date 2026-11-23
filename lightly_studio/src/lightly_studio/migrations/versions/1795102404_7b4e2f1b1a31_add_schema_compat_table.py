"""add schema_compat table.

One row that records the applied schema revision and the lowest client version
that can use it. This revision inserts the row. Each later revision updates it in
its own transaction, see ``schema_compat.on_version_apply``.

Revision ID: 7b4e2f1b1a31
Revises: 1e2ff606de9f
Create Date: 2026-11-19 10:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7b4e2f1b1a31"
down_revision: str | Sequence[str] | None = "1e2ff606de9f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The lowest lightly-studio version that can use the schema of this revision.
# Clients up to 1.4.0 fail on the foreign key of 1e2ff606de9f when they delete a label.
min_client_version = "1.5.0"


def upgrade() -> None:
    """Upgrade schema."""
    schema_compat = op.create_table(
        "schema_compat",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("oss_revision", sa.String(), nullable=False),
        sa.Column("min_client_version", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.bulk_insert(
        schema_compat,
        [{"id": 1, "oss_revision": revision, "min_client_version": min_client_version}],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("schema_compat")
