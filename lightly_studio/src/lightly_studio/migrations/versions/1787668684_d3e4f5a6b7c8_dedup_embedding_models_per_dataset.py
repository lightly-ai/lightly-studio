"""dedup embedding models per dataset.

Collapses duplicate ``embedding_model`` rows within each dataset. Duplicates exist because
the write path deduplicates per collection, so the same model used in two collections of
one dataset produced two rows. For each ``(dataset_id, embedding_model_hash)`` the oldest
row (by ``created_at ASC, embedding_model_id ASC`` -- the same tie-break the default
resolution uses) is kept; ``sample_embedding`` and ``default_embedding_space`` foreign
keys are repointed to it and the duplicates are deleted.

This migration only collapses the data. The matching ``UNIQUE(dataset_id,
embedding_model_hash)`` constraint is added in a later revision, together with the resolver
switch that makes the write path deduplicate per dataset. The constraint cannot land here:
the current write path still deduplicates per collection, so it would insert a duplicate
row for a second collection in the same dataset, which the constraint would reject.

Downgrade is a no-op: the collapsed duplicate rows cannot be reconstructed.

DuckDB builds its schema with ``create_all``, so this migration only matters for tracked
Postgres databases.

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-08-25 10:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, Sequence[str], None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    # Map every model row to the canonical row it collapses into: the oldest row that
    # shares its (dataset_id, embedding_model_hash). A canonical row maps to itself.
    bind.execute(
        sa.text(
            """
            CREATE TEMPORARY TABLE embedding_model_dedup_map AS
            SELECT
                embedding_model_id,
                FIRST_VALUE(embedding_model_id) OVER (
                    PARTITION BY dataset_id, embedding_model_hash
                    ORDER BY created_at ASC, embedding_model_id ASC
                ) AS canonical_id
            FROM embedding_model
            """
        )
    )

    # Drop sample_embedding rows that would collide with the canonical model's own
    # embedding for the same sample after repointing, keeping the (sample_id,
    # embedding_model_id) primary key valid. The same hash means the same model, so the
    # dropped row is redundant.
    bind.execute(
        sa.text(
            """
            DELETE FROM sample_embedding AS se
            USING embedding_model_dedup_map AS m
            WHERE se.embedding_model_id = m.embedding_model_id
              AND m.embedding_model_id <> m.canonical_id
              AND EXISTS (
                  SELECT 1 FROM sample_embedding AS keep
                  WHERE keep.sample_id = se.sample_id
                    AND keep.embedding_model_id = m.canonical_id
              )
            """
        )
    )

    # Repoint the remaining sample_embedding rows to the canonical model.
    bind.execute(
        sa.text(
            """
            UPDATE sample_embedding AS se
            SET embedding_model_id = m.canonical_id
            FROM embedding_model_dedup_map AS m
            WHERE se.embedding_model_id = m.embedding_model_id
              AND m.embedding_model_id <> m.canonical_id
            """
        )
    )

    # Repoint default_embedding_space rows. Its primary key is collection_id, so there is
    # one row per collection and no collision is possible.
    bind.execute(
        sa.text(
            """
            UPDATE default_embedding_space AS des
            SET embedding_model_id = m.canonical_id
            FROM embedding_model_dedup_map AS m
            WHERE des.embedding_model_id = m.embedding_model_id
              AND m.embedding_model_id <> m.canonical_id
            """
        )
    )

    # Delete the now-unreferenced duplicate model rows.
    bind.execute(
        sa.text(
            """
            DELETE FROM embedding_model AS em
            USING embedding_model_dedup_map AS m
            WHERE em.embedding_model_id = m.embedding_model_id
              AND m.embedding_model_id <> m.canonical_id
            """
        )
    )

    bind.execute(sa.text("DROP TABLE embedding_model_dedup_map"))


def downgrade() -> None:
    """Downgrade schema.

    No-op: the collapsed duplicate rows cannot be reconstructed.
    """
