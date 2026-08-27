"""add group component definition table.

Creates the ``group_component_definition`` table (one row per component collection),
backfills it from the ``group_component_name``/``group_component_index`` columns on
``collection``, then drops those columns now that they live on the new table.

DuckDB builds its schema with ``create_all``, so this migration only matters for tracked
Postgres databases.

Revision ID: d4e5f6a7b8c9
Revises: c2d3e4f5a6b7
Create Date: 2026-08-27 09:50:09.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "group_component_definition",
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("group_component_name", sa.String(), nullable=False),
        sa.Column("group_component_index", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["collection_id"], ["collection.collection_id"]),
        sa.PrimaryKeyConstraint("collection_id"),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO group_component_definition
                (collection_id, group_component_name, group_component_index)
            SELECT collection_id, group_component_name, group_component_index
            FROM collection
            WHERE group_component_name IS NOT NULL
            """
        )
    )
    op.drop_column("collection", "group_component_name")
    op.drop_column("collection", "group_component_index")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("collection", sa.Column("group_component_index", sa.Integer(), nullable=True))
    op.add_column("collection", sa.Column("group_component_name", sa.String(), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE collection
            SET group_component_name = group_component_definition.group_component_name,
                group_component_index = group_component_definition.group_component_index
            FROM group_component_definition
            WHERE collection.collection_id = group_component_definition.collection_id
            """
        )
    )
    op.drop_table("group_component_definition")
