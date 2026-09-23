"""add mcap_group_component_definition.

Adds the ``mcap_group_component_definition`` table (1:1 with
``group_component_definition``).
``mcap_data_type`` is a native ``mcapdatatype`` enum storing the member names
``VIDEO_FRAME`` and ``POINT_CLOUD``; ``channel_id`` is the same
integer channel id as on ``mcap`` samples; ``frame_id`` is an optional id used to match
this slot against calibration/transform data.

DuckDB builds its schema with ``create_all``, so this migration only matters for tracked
Postgres databases.

Revision ID: f6a7b8c9d0e1
Revises: f7a8b9c0d1e2
Create Date: 2026-09-09 13:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: str | Sequence[str] | None = "f7a8b9c0d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Native enum type, matching ``sampletype`` on ``collection``. Adding a member later
# needs an ``op.sync_enum_values`` migration.
_MCAP_DATA_TYPE = sa.Enum("VIDEO_FRAME", "POINT_CLOUD", name="mcapdatatype")


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "mcap_group_component_definition",
        sa.Column("mcap_data_type", _MCAP_DATA_TYPE, nullable=False),
        sa.Column("frame_id", sa.String(), nullable=True),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["group_component_definition.collection_id"],
        ),
        sa.PrimaryKeyConstraint("collection_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("mcap_group_component_definition")
    # ``drop_table`` leaves the enum type behind, which breaks a later re-upgrade.
    _MCAP_DATA_TYPE.drop(op.get_bind(), checkfirst=True)
