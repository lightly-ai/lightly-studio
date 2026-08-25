"""drop embedding_model collection_id.

Removes the `collection_id` column (and its index and foreign key) from the
`embedding_model` table. Embedding models become a shared global registry, deduplicated
by hash and no longer scoped to a collection; a collection's default is resolved through
`default_embedding_space` instead.

Before dropping the column, this reruns the `default_embedding_space` backfill from
`b1c2d3e4f5a6` (idempotent via `ON CONFLICT DO NOTHING`), so any collection whose default
row is still missing is seeded from its oldest model while `collection_id` is available.

Downgrade re-adds the column, its foreign key, and its index, but is lossy: the column is
re-added nullable and left empty (no backfill), because the per-collection scoping cannot
be reconstructed once the column is dropped.

DuckDB builds its schema with `create_all`, so this migration only matters for tracked
Postgres databases.

Revision ID: 5855d824582d
Revises: b1c2d3e4f5a6
Create Date: 2026-08-24 14:45:04.339061

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5855d824582d"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    _backfill_defaults()
    op.drop_index(op.f("ix_embedding_model_collection_id"), table_name="embedding_model")
    op.drop_constraint(
        op.f("embedding_model_collection_id_fkey"), "embedding_model", type_="foreignkey"
    )
    op.drop_column("embedding_model", "collection_id")


def downgrade() -> None:
    """Downgrade schema.

    Lossy: the column is re-added nullable and left empty. The old per-collection scoping
    cannot be reconstructed, so there is no backfill.
    """
    op.add_column("embedding_model", sa.Column("collection_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("embedding_model_collection_id_fkey"),
        "embedding_model",
        "collection",
        ["collection_id"],
        ["collection_id"],
    )
    op.create_index(
        op.f("ix_embedding_model_collection_id"),
        "embedding_model",
        ["collection_id"],
        unique=False,
    )


def _backfill_defaults() -> None:
    """Seed one default per collection that still lacks one: its oldest embedding model.

    Mirrors the backfill in `b1c2d3e4f5a6`. `DISTINCT ON` keeps the first row per
    `collection_id` under the `ORDER BY`, so the `created_at ASC, embedding_model_id ASC`
    tie-break selects the oldest model. `ON CONFLICT DO NOTHING` makes the rerun
    idempotent: collections already seeded by PR1b or the write path are left untouched.
    """
    op.get_bind().execute(
        sa.text(
            """
            INSERT INTO default_embedding_space (collection_id, embedding_model_id)
            SELECT DISTINCT ON (collection_id) collection_id, embedding_model_id
            FROM embedding_model
            ORDER BY collection_id, created_at ASC, embedding_model_id ASC
            ON CONFLICT (collection_id) DO NOTHING
            """
        )
    )
