"""Add disposable saved embedding plots."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a3e921f6d502"
down_revision = "e4c3c74ae338"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create plot storage without changing source embeddings or the existing cache."""
    op.create_table(
        "embedding_plot",
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("embedding_model_id", sa.Uuid(), nullable=False),
        sa.Column("is_dirty", sa.Boolean(), nullable=False),
        sa.Column("write_token", sa.Uuid(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("collection_id", "embedding_model_id"),
    )


def downgrade() -> None:
    """Remove derived plots."""
    op.drop_table("embedding_plot")
