"""reshape-two-dim-embeddings.

Revision ID: def3ea185ea7
Revises: e8f9a0b1c2d3
Create Date: 2026-08-13 10:40:18.236504

``two_dim_embeddings`` is a pure cache: every row can be recomputed from
``sample_embedding``. The table is therefore dropped and recreated rather than altered,
which keeps the migration simple and avoids backfilling the new NOT NULL columns. The
projections regenerate on the next request.

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlmodel.sql.sqltypes import AutoString

# revision identifiers, used by Alembic.
revision: str = "def3ea185ea7"
down_revision: Union[str, Sequence[str], None] = "e8f9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table("two_dim_embeddings")
    op.create_table(
        "two_dim_embeddings",
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("embedding_model_id", sa.Uuid(), nullable=False),
        sa.Column("fingerprint", AutoString(), nullable=False),
        sa.Column("sample_ids", sa.ARRAY(sa.Uuid()), nullable=True),
        sa.Column("x", sa.ARRAY(sa.Float()), nullable=True),
        sa.Column("y", sa.ARRAY(sa.Float()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["collection_id"], ["collection.collection_id"]),
        sa.ForeignKeyConstraint(["embedding_model_id"], ["embedding_model.embedding_model_id"]),
        sa.PrimaryKeyConstraint("collection_id", "embedding_model_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("two_dim_embeddings")
    op.create_table(
        "two_dim_embeddings",
        sa.Column("hash", AutoString(), nullable=False),
        sa.Column("x", sa.ARRAY(sa.Float()), nullable=True),
        sa.Column("y", sa.ARRAY(sa.Float()), nullable=True),
        sa.PrimaryKeyConstraint("hash"),
    )
