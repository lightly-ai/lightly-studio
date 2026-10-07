"""drop tag kind column.

Annotations are samples, so a tag is a set of sample ids of any sample type. The ``kind``
column only split the tags of a collection into sample tags and annotation tags. Tag names are
already unique per collection, so the drop cannot cause a name conflict.

The downgrade re-adds ``kind`` as nullable, backfills it, and sets it ``NOT NULL``. A tag
that holds an annotation sample gets ``'annotation'``, all other tags get ``'sample'``.

DuckDB builds its schema with ``create_all`` and has no migration step, so this migration only
matters for tracked Postgres databases.

Revision ID: 3220ed4b892e
Revises: f2a3b4c5d6e7
Create Date: 2026-10-07 10:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3220ed4b892e"
down_revision: str | Sequence[str] | None = "f2a3b4c5d6e7"
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
    # A tag that holds an annotation sample becomes an annotation tag. All other tags,
    # including empty tags, become sample tags.
    op.execute(
        sa.text(
            """
            UPDATE tag SET kind = 'annotation'
            WHERE tag_id IN (
                SELECT link.tag_id
                FROM sampletaglinktable AS link
                JOIN sample ON sample.sample_id = link.sample_id
                JOIN collection ON collection.collection_id = sample.collection_id
                WHERE collection.sample_type = 'ANNOTATION'
            )
            """
        )
    )
    op.execute(sa.text("UPDATE tag SET kind = 'sample' WHERE kind IS NULL"))
    op.alter_column("tag", "kind", existing_type=sa.VARCHAR(), nullable=False)
