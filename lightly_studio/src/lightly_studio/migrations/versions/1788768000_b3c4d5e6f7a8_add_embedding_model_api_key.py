"""add the embedding_model api_key column.

A remote embedding backend authenticates with a bearer token. The token is stored next to the
``remote_embedder_url`` it belongs to, in a nullable ``api_key`` column; being optional, it needs
no backfill. The downgrade drops the column, discarding any stored token.

DuckDB builds its schema with ``create_all``, so this migration only matters for tracked Postgres
databases.

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-09-07 10:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7a8"
down_revision: str | Sequence[str] | None = "a2b3c4d5e6f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "embedding_model",
        sa.Column("api_key", sa.VARCHAR(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema.

    Drops ``api_key``. The stored tokens are lost and have to be set again after an upgrade.
    """
    op.drop_column("embedding_model", "api_key")
