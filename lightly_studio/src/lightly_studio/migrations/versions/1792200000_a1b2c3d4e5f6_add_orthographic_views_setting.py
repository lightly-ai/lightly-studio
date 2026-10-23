"""Add the orthographic views setting.

Revision ID: a1b2c3d4e5f6
Revises: e4c3c74ae338
"""

import sqlalchemy as sa
from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "e4c3c74ae338"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the setting with projections disabled by default."""
    op.add_column(
        "setting",
        sa.Column(
            "show_orthographic_views",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    """Remove the orthographic views setting."""
    op.drop_column("setting", "show_orthographic_views")
