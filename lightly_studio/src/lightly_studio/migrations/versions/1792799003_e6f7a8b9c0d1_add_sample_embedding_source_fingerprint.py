"""Add sample_embedding.source_fingerprint.

Adds a nullable ``source_fingerprint`` column that records the annotation box an
embedding was computed from. Image embeddings and existing rows keep ``NULL``.

Revision ID: e6f7a8b9c0d1
Revises: a3e921f6d502
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e6f7a8b9c0d1"
down_revision: str | Sequence[str] | None = "a3e921f6d502"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # SET LOCAL holds until reset below. env.py runs all revisions in one transaction.
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.add_column(
        "sample_embedding",
        sa.Column("source_fingerprint", sa.String(), nullable=True),
    )
    # Do not hold the timeout for the revisions that run after this one.
    op.execute("SET LOCAL lock_timeout = DEFAULT")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.drop_column("sample_embedding", "source_fingerprint")
    op.execute("SET LOCAL lock_timeout = DEFAULT")
