"""add-temporal-span.

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-07-07 10:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "temporal_span",
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("start_time_s", sa.Float(), nullable=False),
        sa.Column("end_time_s", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["sample_id"], ["sample.sample_id"]),
        sa.PrimaryKeyConstraint("sample_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("temporal_span")
