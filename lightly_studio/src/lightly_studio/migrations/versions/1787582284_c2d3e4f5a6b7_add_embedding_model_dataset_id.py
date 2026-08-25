"""add embedding model dataset id.

Adds ``dataset_id`` to ``embedding_model`` and backfills it through the existing
collection relationship. The column is added as nullable for the backfill and then made
required.

DuckDB builds its schema with ``create_all``, so this migration only matters for tracked
Postgres databases.

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-08-24 16:38:04.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("embedding_model", sa.Column("dataset_id", sa.Uuid(), nullable=True))
    op.create_index(
        op.f("ix_embedding_model_dataset_id"),
        "embedding_model",
        ["dataset_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_embedding_model_dataset_id",
        "embedding_model",
        "dataset",
        ["dataset_id"],
        ["dataset_id"],
    )
    op.execute(
        sa.text(
            """
            UPDATE embedding_model
            SET dataset_id = collection.dataset_id
            FROM collection
            WHERE embedding_model.collection_id = collection.collection_id
            """
        )
    )
    op.alter_column("embedding_model", "dataset_id", nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_embedding_model_dataset_id", "embedding_model", type_="foreignkey")
    op.drop_index(op.f("ix_embedding_model_dataset_id"), table_name="embedding_model")
    op.drop_column("embedding_model", "dataset_id")
