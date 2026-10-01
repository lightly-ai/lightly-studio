"""make tag names unique per collection.

Tag names are shared by sample and annotation tags, so ``kind`` must not be part
of the uniqueness constraint. Existing cross-kind duplicates are consolidated
before the new constraint is created. The sample tag is retained when present,
and links from duplicate tags are merged into the retained tag.

DuckDB builds its schema with ``create_all``, so this migration only applies to
tracked PostgreSQL databases.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-09-16 10:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9d0e1f2a3b4"
down_revision: str | Sequence[str] | None = "b8c9d0e1f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Consolidate duplicate tags and replace the kind-scoped constraint."""
    op.drop_constraint("unique_name_constraint", "tag", type_="unique")
    op.execute(
        sa.text(
            """
            CREATE TEMPORARY TABLE tag_name_duplicate ON COMMIT DROP AS
            WITH ranked_tags AS (
                SELECT
                    tag_id,
                    FIRST_VALUE(tag_id) OVER (
                        PARTITION BY collection_id, name
                        ORDER BY
                            CASE kind WHEN 'sample' THEN 0 ELSE 1 END,
                            created_at,
                            tag_id
                    ) AS canonical_tag_id,
                    ROW_NUMBER() OVER (
                        PARTITION BY collection_id, name
                        ORDER BY
                            CASE kind WHEN 'sample' THEN 0 ELSE 1 END,
                            created_at,
                            tag_id
                    ) AS row_number
                FROM tag
            )
            SELECT tag_id AS duplicate_tag_id, canonical_tag_id
            FROM ranked_tags
            WHERE row_number > 1
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO sampletaglinktable (sample_id, tag_id)
            SELECT link.sample_id, duplicate.canonical_tag_id
            FROM sampletaglinktable AS link
            JOIN tag_name_duplicate AS duplicate
                ON duplicate.duplicate_tag_id = link.tag_id
            ON CONFLICT (sample_id, tag_id) DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM sampletaglinktable AS link
            USING tag_name_duplicate AS duplicate
            WHERE link.tag_id = duplicate.duplicate_tag_id
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM tag
            USING tag_name_duplicate AS duplicate
            WHERE tag.tag_id = duplicate.duplicate_tag_id
            """
        )
    )
    op.drop_table("tag_name_duplicate")
    op.create_unique_constraint("unique_name_constraint", "tag", ["collection_id", "name"])


def downgrade() -> None:
    """Restore the former kind-scoped tag-name constraint."""
    op.drop_constraint("unique_name_constraint", "tag", type_="unique")
    op.create_unique_constraint("unique_name_constraint", "tag", ["collection_id", "kind", "name"])
