"""Add image interpolation setting.

Revision ID: 8cb37a9d104e
Revises: 94ca81e6b023
"""

import sqlalchemy as sa
from alembic import op

revision = "8cb37a9d104e"
down_revision = "94ca81e6b023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add image interpolation with a default for existing settings."""
    op.add_column(
        "setting",
        sa.Column("image_interpolation", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    """Remove image interpolation."""
    op.drop_column("setting", "image_interpolation")
