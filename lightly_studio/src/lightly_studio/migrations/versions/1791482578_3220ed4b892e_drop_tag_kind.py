"""drop tag kind column.

A tag holds only samples of its own collection, so the sample type of the collection gives the
kind of the tag. The ``kind`` column only repeats that information. Tag names are already unique
per collection, so the drop cannot cause a name conflict.

The downgrade re-adds ``kind`` as nullable, backfills it from the sample type of the collection
of each tag, and sets it ``NOT NULL``. A tag of an annotation collection gets ``'annotation'``.
All other tags get ``'sample'``, the default of the column. This includes a tag whose
collection was deleted.

DuckDB builds its schema with ``create_all`` and has no migration step, so this migration only
matters for tracked Postgres databases.

Revision ID: 3220ed4b892e
Revises: 68fcd3378db6
Create Date: 2026-10-08 18:02:58.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3220ed4b892e"
down_revision: str | Sequence[str] | None = "68fcd3378db6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("tag", "kind")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "tag",
        sa.Column("kind", sa.VARCHAR(), autoincrement=False, nullable=True),
    )
    # The subquery is NULL for a tag whose collection was deleted, so that tag gets 'sample'.
    op.execute(
        sa.text(
            """
            UPDATE tag SET kind = CASE (
                SELECT collection.sample_type
                FROM collection
                WHERE collection.collection_id = tag.collection_id
            )
                WHEN 'ANNOTATION' THEN 'annotation'
                ELSE 'sample'
            END
            """
        )
    )
    op.alter_column("tag", "kind", existing_type=sa.VARCHAR(), nullable=False)
