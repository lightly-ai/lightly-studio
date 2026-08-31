"""rekey embedding_model_hash to the space key.

Earlier releases stored a checkpoint file hash in ``embedding_model_hash`` while
``name`` held the model name. The write path now keys the row by the generator's
``space_key`` and, for the built-in generators, ``space_key`` equals ``name``. So the
registration lookup (``get_by_model_hash``) no longer finds these rows: it would insert
a duplicate and violate ``unique_embedding_model_name``.

This migration realigns existing rows by setting ``embedding_model_hash = name``. After
the update ``embedding_model_hash`` equals ``name``, which is already unique per dataset
(``unique_embedding_model_name``), so ``unique_embedding_model_hash`` still holds.

The original file hashes are overwritten and cannot be recomputed here, so the downgrade
cannot restore them. Few-shot classifier exports saved under the old scheme still carry
the old hash and will not resolve after this change; re-creating them is expected.

DuckDB builds its schema with ``create_all`` and has no backfill step, so this migration
only matters for tracked Postgres databases.

Revision ID: f1a2b3c4d5e6
Revises: d117a91bf587
Create Date: 2026-08-31 09:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: str | Sequence[str] | None = "d117a91bf587"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Realign the hash to the space key, which equals the name for built-in generators.
    # Only rows that still carry the old file hash are touched.
    op.execute(
        sa.text(
            "UPDATE embedding_model SET embedding_model_hash = name "
            "WHERE embedding_model_hash <> name"
        )
    )


def downgrade() -> None:
    """Downgrade schema.

    Irreversible: the original checkpoint file hashes were overwritten and cannot be
    reconstructed, so this is a no-op.
    """
