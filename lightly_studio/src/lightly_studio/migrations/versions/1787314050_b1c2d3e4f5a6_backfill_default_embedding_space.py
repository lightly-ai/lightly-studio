"""backfill default embedding space.

Seeds the `default_embedding_space` table (created empty in `a05138ab5fc4`) with each
collection's default: the oldest embedding model by `created_at ASC, embedding_model_id
ASC`. This is the same model the query resolved before, so reading the table
resolves the same model the query used before. Collections created after this migration
are populated by `embedding_manager.register_embedding_model`, so no collection is left
without a default row.

Downgrade empties the table. It is not lossy at this revision: `embedding_model` still
carries `collection_id`, so the default can be re-derived from the same oldest-model
rule (the column drop lands in a later revision).

DuckDB builds its schema with `create_all` and has no backfill step, so this migration
only matters for tracked Postgres databases.

Revision ID: b1c2d3e4f5a6
Revises: a05138ab5fc4
Create Date: 2026-08-21 14:12:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "a05138ab5fc4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    _backfill_defaults()


def downgrade() -> None:
    """Downgrade schema."""
    op.get_bind().execute(sa.text("DELETE FROM default_embedding_space"))


def _backfill_defaults() -> None:
    """Seed one default per collection: its oldest embedding model.

    `DISTINCT ON` keeps the first row per `collection_id` under the `ORDER BY`, so the
    `created_at ASC, embedding_model_id ASC` tie-break selects the oldest model.
    """
    op.get_bind().execute(
        sa.text(
            """
            INSERT INTO default_embedding_space (collection_id, embedding_model_id)
            SELECT DISTINCT ON (collection_id) collection_id, embedding_model_id
            FROM embedding_model
            ORDER BY collection_id, created_at ASC, embedding_model_id ASC
            """
        )
    )
