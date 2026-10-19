"""add assisted_labeling_provider setting.

Revision ID: a3c5e7f9b1d2
Revises: f2a3b4c5d6e7
Create Date: 2026-10-07 10:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlmodel.sql.sqltypes import AutoString

# revision identifiers, used by Alembic.
revision: str = "a3c5e7f9b1d2"
down_revision: str | Sequence[str] | None = "f2a3b4c5d6e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "setting",
        sa.Column(
            "assisted_labeling_provider",
            AutoString(),
            server_default="fal_sam3",
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("setting", "assisted_labeling_provider")
