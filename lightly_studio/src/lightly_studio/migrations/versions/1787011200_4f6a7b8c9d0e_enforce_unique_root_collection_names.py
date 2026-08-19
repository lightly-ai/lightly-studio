"""enforce_unique_root_collection_names.

Adds a partial unique index on `collection(name) WHERE parent_collection_id IS NULL`.

`UniqueConstraint("name", "parent_collection_id")` on the `collection` table does not
prevent duplicate root-collection names: Postgres treats NULL `parent_collection_id`
values as distinct, so any number of root collections (parent_collection_id IS NULL)
can share a name. This index closes that gap for root collections specifically; the
existing constraint continues to cover non-root collections.

This index is Postgres-only and intentionally not declared on `CollectionTable` in
`models/collection.py`: DuckDB (schema created via `create_all()`) does not support
partial indexes. Autogenerate would therefore propose dropping this index when it diffs
the live catalog against SQLModel metadata; `_include_object` in `migrations/env.py`
excludes it from those diffs.

Revision ID: 4f6a7b8c9d0e
Revises: a3b4c5d6e7f8
Create Date: 2026-08-18 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4f6a7b8c9d0e"
down_revision: Union[str, Sequence[str], None] = "a3b4c5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX_NAME = "uq_collection_name_root"


def upgrade() -> None:
    """Upgrade schema."""
    duplicates = (
        op.get_bind()
        .execute(
            sa.text(
                """
            SELECT name, COUNT(*)
            FROM collection
            WHERE parent_collection_id IS NULL
            GROUP BY name
            HAVING COUNT(*) > 1
            """
            )
        )
        .fetchall()
    )
    if duplicates:
        # Name the duplicates: this migration runs on startup, so an operator has no
        # way to list them from within the app once it fails to boot.
        names = ", ".join(f"'{name}' ({count} collections)" for name, count in duplicates)
        raise RuntimeError(
            "Cannot add unique index, duplicate root-collection names found: "
            f"{names}. Rename or merge the duplicates before migrating."
        )

    op.create_index(
        _INDEX_NAME,
        "collection",
        ["name"],
        unique=True,
        postgresql_where=sa.text("parent_collection_id IS NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(_INDEX_NAME, table_name="collection")
