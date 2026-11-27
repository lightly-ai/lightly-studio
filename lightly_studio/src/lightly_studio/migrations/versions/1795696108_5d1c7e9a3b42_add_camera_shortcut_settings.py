"""Add camera shortcut settings.

Revision ID: 5d1c7e9a3b42
Revises: 37ee066f0639
"""

import sqlalchemy as sa
from alembic import op

revision = "5d1c7e9a3b42"
down_revision = "37ee066f0639"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add previous and next camera shortcuts with defaults for existing settings."""
    op.add_column(
        "setting",
        sa.Column("key_previous_camera", sa.String(), nullable=False, server_default="["),
    )
    op.add_column(
        "setting",
        sa.Column("key_next_camera", sa.String(), nullable=False, server_default="]"),
    )


def downgrade() -> None:
    """Remove previous and next camera shortcuts."""
    op.drop_column("setting", "key_next_camera")
    op.drop_column("setting", "key_previous_camera")
