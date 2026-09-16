"""make tag names unique per collection.

Tag names are shared by sample and annotation tags, so ``kind`` must not be part
of the uniqueness constraint. Existing databases containing a sample tag and an
annotation tag with the same name in one collection cannot be upgraded until one
of those tags is renamed or removed. PostgreSQL executes this migration
transactionally, so a failed constraint creation leaves the prior constraint in
place.

DuckDB builds its schema with ``create_all``, so this migration only applies to
tracked PostgreSQL databases.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-09-16 10:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8c9d0e1f2a3"
down_revision: str | Sequence[str] | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Replace the kind-scoped tag-name constraint."""
    op.drop_constraint("unique_name_constraint", "tag", type_="unique")
    op.create_unique_constraint("unique_name_constraint", "tag", ["collection_id", "name"])


def downgrade() -> None:
    """Restore the former kind-scoped tag-name constraint."""
    op.drop_constraint("unique_name_constraint", "tag", type_="unique")
    op.create_unique_constraint("unique_name_constraint", "tag", ["collection_id", "kind", "name"])
