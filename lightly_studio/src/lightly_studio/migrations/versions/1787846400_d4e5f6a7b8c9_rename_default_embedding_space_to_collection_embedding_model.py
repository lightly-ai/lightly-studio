"""rename default embedding space to collection embedding model.

Renames the `default_embedding_space` table to `collection_embedding_model` and adds an
`is_default` flag. The current contents are dropped and re-seeded from `embedding_model`:
one row per model, so a collection with several models gets a row for each. Only the
oldest model per collection (by `created_at ASC, embedding_model_id ASC`) is the default,
with `is_default = true`; the rest are `false`.

Re-seeding from `embedding_model` keeps this migration independent of the table's prior
contents. The prior `default_embedding_space` rows held only the defaults, which this
backfill reproduces from `embedding_model`, so dropping them loses nothing. It reads
`embedding_model.collection_id`, which still exists at this revision (its drop lands in a
later revision). This table is where `collection_id` moves to as it is removed from
`embedding_model`.

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
    # A collection may now use several embedding models, so the primary key becomes the
    # (collection_id, embedding_model_id) pair. Renaming the table left the old key
    # constraint under its original name, so drop it before adding the composite one.
    op.drop_constraint(
        "default_embedding_space_pkey", "collection_embedding_model", type_="primary"
    )
    op.create_primary_key(
        "collection_embedding_model_pkey",
        "collection_embedding_model",
        ["collection_id", "embedding_model_id"],
    )
    _backfill_collection_embedding_models()
    # At most one default embedding model per collection. Postgres-only: DuckDB cannot
    # create partial indexes, so on DuckDB the invariant is not enforced at the database
    # level and callers must maintain it.
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
    op.drop_constraint(
        "collection_embedding_model_pkey", "collection_embedding_model", type_="primary"
    )
    op.create_primary_key(
        "default_embedding_space_pkey", "collection_embedding_model", ["collection_id"]
    )
    op.drop_column("collection_embedding_model", "is_default")
    op.rename_table("collection_embedding_model", "default_embedding_space")


def _backfill_collection_embedding_models() -> None:
    """Seed every embedding model per collection, the oldest one as the default.

    Each `embedding_model` row becomes one `collection_embedding_model` row. `ROW_NUMBER`
    ranks a collection's models by `created_at ASC, embedding_model_id ASC`, so rank 1 is
    the oldest; only that row gets `is_default = true`, which satisfies the one-default
    -per-collection partial unique index.
    """
    op.get_bind().execute(
        sa.text(
            """
            INSERT INTO collection_embedding_model (collection_id, embedding_model_id, is_default)
            SELECT
                collection_id,
                embedding_model_id,
                ROW_NUMBER() OVER (
                    PARTITION BY collection_id
                    ORDER BY created_at ASC, embedding_model_id ASC
                ) = 1 AS is_default
            FROM embedding_model
            """
        )
    )
