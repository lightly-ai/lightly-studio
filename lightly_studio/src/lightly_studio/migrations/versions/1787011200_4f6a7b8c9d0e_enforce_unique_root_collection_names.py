"""enforce_unique_root_collection_names.

Adds a partial unique index on `collection(name) WHERE parent_collection_id IS NULL`.
`UniqueConstraint("name", "parent_collection_id")` misses root collections because
Postgres compares NULL parents as distinct. Existing duplicates are renamed first, see
`_rename_duplicate_root_collections`.

The index is Postgres-only: DuckDB cannot create partial indexes, so it is not declared
on `CollectionTable` and `_include_object` in `migrations/env.py` keeps autogenerate from
dropping it.

Revision ID: 4f6a7b8c9d0e
Revises: a3b4c5d6e7f8
Create Date: 2026-08-18 00:00:00.000000

"""

import logging
from collections.abc import Sequence
from typing import Any, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4f6a7b8c9d0e"
down_revision: Union[str, Sequence[str], None] = "a3b4c5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX_NAME = "uq_collection_name_root"

_logger = logging.getLogger("lightly_studio.migrations")


def upgrade() -> None:
    """Upgrade schema."""
    _rename_duplicate_root_collections()

    op.create_index(
        _INDEX_NAME,
        "collection",
        ["name"],
        unique=True,
        postgresql_where=sa.text("parent_collection_id IS NULL"),
    )


def downgrade() -> None:
    """Downgrade schema. Renamed collections keep their new names."""
    op.drop_index(_INDEX_NAME, table_name="collection")


def _rename_duplicate_root_collections() -> None:
    """Renames root collections that share a name so the unique index can be created.

    The oldest collection of each name keeps it, the others get the first free
    ` (<number>)` suffix. Renaming instead of failing the migration keeps the app
    bootable, `run_migrations` is called from `DatabaseEngine.__init__`. Merging is not an
    option, root collections are separate datasets with their own samples.
    """
    connection = op.get_bind()
    collections = connection.execute(
        sa.text(
            """
            SELECT collection_id, name
            FROM collection
            WHERE parent_collection_id IS NULL
            ORDER BY name, created_at, collection_id
            """
        )
    ).fetchall()

    taken = {name for _, name in collections}
    seen: set[str] = set()
    renames: list[dict[str, Any]] = []
    for collection_id, name in collections:
        if name not in seen:
            seen.add(name)
            continue
        # `taken` holds every existing name, so the suffix cannot take a name that
        # another root collection still uses.
        new_name = _free_name(name=name, taken=taken)
        taken.add(new_name)
        renames.append({"collection_id": collection_id, "name": new_name})
        _logger.warning("Renaming duplicate root collection '%s' to '%s'.", name, new_name)

    if renames:
        connection.execute(
            sa.text("UPDATE collection SET name = :name WHERE collection_id = :collection_id"),
            renames,
        )


def _free_name(name: str, taken: set[str]) -> str:
    """Returns `name` with the lowest ` (<number>)` suffix that is not in `taken`."""
    number = 2
    while f"{name} ({number})" in taken:
        number += 1
    return f"{name} ({number})"
