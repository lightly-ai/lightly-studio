"""add default embedding space table.

Creates the empty `default_embedding_space` table (one row per collection). No code reads
the table at this revision.

DuckDB builds its schema with `create_all`, so this migration only matters for tracked
Postgres databases.

Revision ID: a05138ab5fc4
Revises: 4f6a7b8c9d0e
Create Date: 2026-08-21 14:07:29.909594

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a05138ab5fc4"
down_revision: Union[str, Sequence[str], None] = "4f6a7b8c9d0e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "default_embedding_space",
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("embedding_model_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["collection_id"], ["collection.collection_id"]),
        sa.ForeignKeyConstraint(["embedding_model_id"], ["embedding_model.embedding_model_id"]),
        sa.PrimaryKeyConstraint("collection_id"),
    )
    op.create_index(
        op.f("ix_default_embedding_space_embedding_model_id"),
        "default_embedding_space",
        ["embedding_model_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_default_embedding_space_embedding_model_id"),
        table_name="default_embedding_space",
    )
    op.drop_table("default_embedding_space")
