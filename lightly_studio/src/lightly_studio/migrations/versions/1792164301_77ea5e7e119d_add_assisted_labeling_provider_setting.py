"""Add assisted labeling provider setting.

Revision ID: 77ea5e7e119d
Revises: d5e6f7a8b9c0
"""

import sqlalchemy as sa
from alembic import op

revision = "77ea5e7e119d"
down_revision = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the assisted labeling provider with a default for existing settings."""
    op.add_column(
        "setting",
        sa.Column(
            "assisted_labeling_provider",
            sa.String(),
            nullable=False,
            server_default="fal_sam3",
        ),
    )


def downgrade() -> None:
    """Remove the assisted labeling provider."""
    op.drop_column("setting", "assisted_labeling_provider")
