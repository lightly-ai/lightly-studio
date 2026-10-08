"""move tag links to the collection of their sample.

A tag belongs to the collection of the samples it tags. Older databases can have a tag
that holds samples of another collection, for example an annotation tag on the image
collection that holds annotations of several annotation collections.

For each such link, the migration gets or creates a tag with the same name in the
collection of the sample and moves the link to it. A new tag gets the kind that matches
the sample type of its collection. A tag that has no links after the move is deleted.

The downgrade does nothing. The moved links stay valid on the previous revision.

DuckDB builds its schema with ``create_all``, so this migration only applies to tracked
PostgreSQL databases.

Revision ID: 68fcd3378db6
Revises: 94ca81e6b023
Create Date: 2026-10-08 10:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "68fcd3378db6"
down_revision: str | Sequence[str] | None = "94ca81e6b023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Move each tag link to a tag in the collection of its sample."""
    op.execute(
        sa.text(
            """
            CREATE TEMPORARY TABLE stray_tag_link ON COMMIT DROP AS
            SELECT
                link.sample_id,
                link.tag_id,
                tag.name,
                sample.collection_id AS sample_collection_id
            FROM sampletaglinktable AS link
            JOIN tag ON tag.tag_id = link.tag_id
            JOIN sample ON sample.sample_id = link.sample_id
            WHERE sample.collection_id <> tag.collection_id
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO tag (tag_id, collection_id, name, kind, created_at, updated_at)
            SELECT
                gen_random_uuid(),
                stray.sample_collection_id,
                stray.name,
                CASE collection.sample_type WHEN 'ANNOTATION' THEN 'annotation' ELSE 'sample' END,
                NOW(),
                NOW()
            FROM (
                SELECT DISTINCT sample_collection_id, name FROM stray_tag_link
            ) AS stray
            JOIN collection ON collection.collection_id = stray.sample_collection_id
            ON CONFLICT (collection_id, name) DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO sampletaglinktable (sample_id, tag_id)
            SELECT stray.sample_id, tag.tag_id
            FROM stray_tag_link AS stray
            JOIN tag
                ON tag.collection_id = stray.sample_collection_id
                AND tag.name = stray.name
            ON CONFLICT (sample_id, tag_id) DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM sampletaglinktable AS link
            USING stray_tag_link AS stray
            WHERE link.sample_id = stray.sample_id AND link.tag_id = stray.tag_id
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM tag
            WHERE tag.tag_id IN (SELECT tag_id FROM stray_tag_link)
            AND NOT EXISTS (
                SELECT 1 FROM sampletaglinktable AS link WHERE link.tag_id = tag.tag_id
            )
            """
        )
    )
    op.drop_table("stray_tag_link")


def downgrade() -> None:
    """Do nothing. The moved links are valid on the previous revision."""
