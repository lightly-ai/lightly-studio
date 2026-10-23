"""Add sample_embedding.source_fingerprint.

Adds a nullable ``source_fingerprint`` column that records the annotation box an
embedding was computed from. Image embeddings and existing rows keep ``NULL``.

Revision ID: e6f7a8b9c0d1
Revises: e4c3c74ae338
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e6f7a8b9c0d1"
down_revision: str | Sequence[str] | None = "e4c3c74ae338"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # SET LOCAL holds for the rest of the upgrade transaction. env.py runs all revisions
    # in one transaction.
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.add_column(
        "sample_embedding",
        sa.Column("source_fingerprint", sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.drop_column("sample_embedding", "source_fingerprint")
