"""Remove the unused hash-based embedding plot cache."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlmodel.sql.sqltypes import AutoString

revision = "b7d24e8f913a"
down_revision = "a3e921f6d502"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Drop the old cache; saved plots and source embeddings are separate tables."""
    op.drop_table("two_dim_embeddings")


def downgrade() -> None:
    """Restore an empty cache; old readers regenerate its derived coordinates."""
    op.create_table(
        "two_dim_embeddings",
        sa.Column("hash", AutoString(), nullable=False),
        sa.Column("x", sa.ARRAY(sa.Float()), nullable=True),
        sa.Column("y", sa.ARRAY(sa.Float()), nullable=True),
        sa.PrimaryKeyConstraint("hash"),
    )
