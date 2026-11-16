"""Add a custom color and opacity to annotation labels."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlmodel.sql.sqltypes import AutoString

revision = "8660d246e98e"
down_revision = "b7d24e8f913a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add nullable color columns; null means the default color."""
    op.add_column("annotation_label", sa.Column("color", AutoString(), nullable=True))
    op.add_column("annotation_label", sa.Column("alpha", sa.Float(), nullable=True))


def downgrade() -> None:
    """Drop the color columns."""
    op.drop_column("annotation_label", "alpha")
    op.drop_column("annotation_label", "color")
