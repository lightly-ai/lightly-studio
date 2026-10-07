"""Add AI-assisted labeling shortcut.

Revision ID: 94ca81e6b023
Revises: f2a3b4c5d6e7
"""

import sqlalchemy as sa
from alembic import op

revision = "94ca81e6b023"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the shortcut with a default for existing settings."""
    op.add_column(
        "setting", sa.Column("key_toolbar_slic", sa.String(), nullable=False, server_default="a")
    )


def downgrade() -> None:
    """Remove the shortcut."""
    op.drop_column("setting", "key_toolbar_slic")
