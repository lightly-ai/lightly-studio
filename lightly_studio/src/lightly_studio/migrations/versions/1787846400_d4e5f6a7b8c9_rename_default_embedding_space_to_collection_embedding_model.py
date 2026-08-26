"""rename default embedding space to collection embedding model.

Renames the `default_embedding_space` table to `collection_embedding_model` and adds an
`is_default` flag. The current contents are dropped and re-seeded from `embedding_model`
(the oldest model per collection by `created_at ASC, embedding_model_id ASC`, the same
rule the earlier backfill used), so every seeded row is a default and `is_default` is
`true`.

Re-seeding from `embedding_model` keeps this migration independent of the table's prior
contents. It reads `embedding_model.collection_id`, which still exists at this revision
(its drop lands in a later revision).

A partial unique index then enforces at most one default per collection. It is
Postgres-only (DuckDB cannot create partial indexes), so it is not declared on
`CollectionEmbeddingModelTable` and `_include_object` in `migrations/env.py` keeps
autogenerate from dropping it.

DuckDB builds its schema with `create_all` and has no backfill step, so this migration
only matters for tracked Postgres databases.

Revision ID: d4e5f6a7b8c9
Revises: c2d3e4f5a6b7
Create Date: 2026-08-26 10:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table("default_embedding_space", "collection_embedding_model")
    # Empty first so the new NOT NULL column needs no server default; the rows are
    # re-seeded below.
    op.get_bind().execute(sa.text("DELETE FROM collection_embedding_model"))
    op.add_column(
        "collection_embedding_model",
        sa.Column("is_default", sa.Boolean(), nullable=False),
    )
    _backfill_defaults()
    # At most one default embedding model per collection.
    op.create_index(
        "uq_collection_embedding_model_default",
        "collection_embedding_model",
        ["collection_id"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_collection_embedding_model_default", table_name="collection_embedding_model")
    op.drop_column("collection_embedding_model", "is_default")
    op.rename_table("collection_embedding_model", "default_embedding_space")


def _backfill_defaults() -> None:
    """Seed one default per collection: its oldest embedding model.

    `DISTINCT ON` keeps the first row per `collection_id` under the `ORDER BY`, so the
    `created_at ASC, embedding_model_id ASC` tie-break selects the oldest model.
    """
    op.get_bind().execute(
        sa.text(
            """
            INSERT INTO collection_embedding_model (collection_id, embedding_model_id, is_default)
            SELECT DISTINCT ON (collection_id) collection_id, embedding_model_id, true
            FROM embedding_model
            ORDER BY collection_id, created_at ASC, embedding_model_id ASC
            """
        )
    )
