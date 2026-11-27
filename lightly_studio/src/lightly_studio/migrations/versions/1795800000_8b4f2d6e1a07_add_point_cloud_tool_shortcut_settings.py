"""Add point cloud tool shortcut settings.

Revision ID: 8b4f2d6e1a07
Revises: 5d1c7e9a3b42
"""

import sqlalchemy as sa
from alembic import op

revision = "8b4f2d6e1a07"
down_revision = "5d1c7e9a3b42"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add select and create cuboid tool shortcuts with defaults for existing settings."""
    op.add_column(
        "setting",
        sa.Column("key_point_cloud_select", sa.String(), nullable=False, server_default="q"),
    )
    op.add_column(
        "setting",
        sa.Column("key_point_cloud_create_cuboid", sa.String(), nullable=False, server_default="c"),
    )


def downgrade() -> None:
    """Remove select and create cuboid tool shortcuts."""
    op.drop_column("setting", "key_point_cloud_create_cuboid")
    op.drop_column("setting", "key_point_cloud_select")
