"""add-export-job.

Revision ID: e8f9a0b1c2d3
Revises: c3d4e5f6a7b8
Create Date: 2026-07-24 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e8f9a0b1c2d3"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "export_job",
        sa.Column("export_key", sa.Uuid(), nullable=False),
        sa.Column("export_path", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("export_key"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("export_job")
