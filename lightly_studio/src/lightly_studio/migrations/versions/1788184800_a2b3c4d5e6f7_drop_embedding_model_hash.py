"""drop embedding_model_hash column.

The write path now keys embedding models by ``name`` (the generator's ``space_key``), and
the ``unique_embedding_model_name`` constraint on ``(dataset_id, name)`` already enforces
uniqueness. The previous migration (``f1a2b3c4d5e6``) set ``embedding_model_hash = name`` on
every row, so the column is redundant. This migration drops the
``unique_embedding_model_hash`` constraint and then the column.

The downgrade re-adds the column as nullable, backfills it from ``name``, sets it ``NOT NULL``,
and re-adds the constraint. The original checkpoint file hashes were already overwritten by
``f1a2b3c4d5e6`` and cannot be reconstructed, so the backfill uses ``name``.

DuckDB builds its schema with ``create_all`` and has no backfill step, so this migration only
matters for tracked Postgres databases.

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-08-31 10:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: str | Sequence[str] | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint("unique_embedding_model_hash", "embedding_model", type_="unique")
    op.drop_column("embedding_model", "embedding_model_hash")


def downgrade() -> None:
    """Downgrade schema.

    Re-adds the column and backfills it from ``name``. The original file hashes cannot be
    reconstructed, so the backfilled value equals ``name``.
    """
    op.add_column(
        "embedding_model",
        sa.Column(
            "embedding_model_hash",
            sa.VARCHAR(length=128),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.execute(sa.text("UPDATE embedding_model SET embedding_model_hash = name"))
    op.alter_column(
        "embedding_model",
        "embedding_model_hash",
        existing_type=sa.VARCHAR(length=128),
        nullable=False,
    )
    op.create_unique_constraint(
        "unique_embedding_model_hash", "embedding_model", ["dataset_id", "embedding_model_hash"]
    )
