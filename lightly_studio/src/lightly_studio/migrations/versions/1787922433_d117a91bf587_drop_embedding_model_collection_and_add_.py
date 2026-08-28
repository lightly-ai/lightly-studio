"""drop embedding model collection and add unique constraints.

Removes ``collection_id`` and ``parameter_count_in_mb`` from ``embedding_model`` and makes
the model unique per dataset with ``(dataset_id, name)`` and ``(dataset_id, embedding_model_hash)``
constraints.

Before the constraints are added, duplicate rows are collapsed. The write path used to
deduplicate per collection, so the same model registered under several collections of one
dataset produced one row per collection. The oldest row per ``(dataset_id,
embedding_model_hash)`` (by ``created_at ASC, embedding_model_id ASC``, matching the reader)
is kept as canonical; ``sample_embedding`` and ``collection_embedding_model`` references are
repointed to it and the duplicate rows are deleted. Collapsing duplicates is lossy, so the
downgrade cannot restore the removed rows.

``embedding_model_hash`` also becomes ``NOT NULL``. Pre-existing NULL hashes are backfilled to
"" before the collapse so they merge into a single row per dataset.

DuckDB builds its schema with ``create_all`` and has no backfill step, so this migration only
matters for tracked Postgres databases.

Revision ID: d117a91bf587
Revises: e5f6a7b8c9d0
Create Date: 2026-08-28 15:07:13.439745

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d117a91bf587"
down_revision: str | Sequence[str] | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Backfill NULL hashes to "" before deduplicating so former-NULL rows collapse together
    # with the "=" join (NULL = NULL is unknown, so NULLs would otherwise survive) and the
    # NOT NULL constraint below can be added.
    op.execute(
        sa.text(
            "UPDATE embedding_model SET embedding_model_hash = '' "
            "WHERE embedding_model_hash IS NULL"
        )
    )
    _deduplicate_embedding_models()
    op.alter_column(
        "embedding_model",
        "embedding_model_hash",
        existing_type=sa.VARCHAR(length=128),
        nullable=False,
    )
    op.create_unique_constraint(
        "unique_embedding_model_hash", "embedding_model", ["dataset_id", "embedding_model_hash"]
    )
    op.create_unique_constraint(
        "unique_embedding_model_name", "embedding_model", ["dataset_id", "name"]
    )
    op.drop_index(op.f("ix_embedding_model_collection_id"), table_name="embedding_model")
    op.drop_constraint(
        op.f("embedding_model_collection_id_fkey"), "embedding_model", type_="foreignkey"
    )
    op.drop_column("embedding_model", "parameter_count_in_mb")
    op.drop_column("embedding_model", "collection_id")


def downgrade() -> None:
    """Downgrade schema.

    Best-effort and lossy: the duplicate rows collapsed on upgrade cannot be restored.
    ``collection_id`` is backfilled from ``collection_embedding_model``, preferring the
    default link, so a model that now belongs to several collections keeps only one.
    """
    op.add_column(
        "embedding_model",
        sa.Column("parameter_count_in_mb", sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "embedding_model",
        sa.Column("collection_id", sa.Uuid(), autoincrement=False, nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE embedding_model AS em
            SET collection_id = link.collection_id
            FROM (
                SELECT DISTINCT ON (embedding_model_id)
                    embedding_model_id, collection_id
                FROM collection_embedding_model
                ORDER BY embedding_model_id, is_default DESC, collection_id ASC
            ) AS link
            WHERE link.embedding_model_id = em.embedding_model_id
            """
        )
    )
    op.alter_column("embedding_model", "collection_id", nullable=False)
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
    op.drop_constraint("unique_embedding_model_name", "embedding_model", type_="unique")
    op.drop_constraint("unique_embedding_model_hash", "embedding_model", type_="unique")
    op.alter_column(
        "embedding_model",
        "embedding_model_hash",
        existing_type=sa.VARCHAR(length=128),
        nullable=True,
    )


def _deduplicate_embedding_models() -> None:
    """Collapse embedding models that share ``(dataset_id, embedding_model_hash)``.

    The oldest row per ``(dataset_id, embedding_model_hash)`` becomes canonical.
    ``sample_embedding`` and ``collection_embedding_model`` references are repointed to it;
    rows that would collide with an existing reference on the canonical model are dropped
    first, then the duplicate models are deleted.
    """
    bind = op.get_bind()
    # Map each duplicate model to its canonical (oldest) row within the same dataset and hash.
    bind.execute(
        sa.text(
            """
            CREATE TEMPORARY TABLE embedding_model_dedup AS
            SELECT
                em.embedding_model_id AS duplicate_id,
                canonical.embedding_model_id AS canonical_id
            FROM embedding_model AS em
            JOIN (
                SELECT DISTINCT ON (dataset_id, embedding_model_hash)
                    dataset_id, embedding_model_hash, embedding_model_id
                FROM embedding_model
                ORDER BY dataset_id, embedding_model_hash, created_at ASC, embedding_model_id ASC
            ) AS canonical
                ON canonical.dataset_id = em.dataset_id
               AND canonical.embedding_model_hash = em.embedding_model_hash
            WHERE em.embedding_model_id <> canonical.embedding_model_id
            """
        )
    )
    # Drop duplicate-model embeddings where the sample already has one on the canonical model.
    bind.execute(
        sa.text(
            """
            DELETE FROM sample_embedding AS se
            USING embedding_model_dedup AS d
            WHERE se.embedding_model_id = d.duplicate_id
              AND EXISTS (
                  SELECT 1 FROM sample_embedding AS existing
                  WHERE existing.sample_id = se.sample_id
                    AND existing.embedding_model_id = d.canonical_id
              )
            """
        )
    )
    # Repoint the remaining duplicate-model embeddings onto the canonical model.
    bind.execute(
        sa.text(
            """
            UPDATE sample_embedding AS se
            SET embedding_model_id = d.canonical_id
            FROM embedding_model_dedup AS d
            WHERE se.embedding_model_id = d.duplicate_id
            """
        )
    )
    # Drop duplicate-model links where the collection already links the canonical model.
    bind.execute(
        sa.text(
            """
            DELETE FROM collection_embedding_model AS cem
            USING embedding_model_dedup AS d
            WHERE cem.embedding_model_id = d.duplicate_id
              AND EXISTS (
                  SELECT 1 FROM collection_embedding_model AS existing
                  WHERE existing.collection_id = cem.collection_id
                    AND existing.embedding_model_id = d.canonical_id
              )
            """
        )
    )
    # Repoint the remaining duplicate-model links onto the canonical model.
    bind.execute(
        sa.text(
            """
            UPDATE collection_embedding_model AS cem
            SET embedding_model_id = d.canonical_id
            FROM embedding_model_dedup AS d
            WHERE cem.embedding_model_id = d.duplicate_id
            """
        )
    )
    # Delete the now-unreferenced duplicate models.
    bind.execute(
        sa.text(
            """
            DELETE FROM embedding_model AS em
            USING embedding_model_dedup AS d
            WHERE em.embedding_model_id = d.duplicate_id
            """
        )
    )
    # Drop the temporary mapping table now that the merge is complete.
    bind.execute(sa.text("DROP TABLE embedding_model_dedup"))
