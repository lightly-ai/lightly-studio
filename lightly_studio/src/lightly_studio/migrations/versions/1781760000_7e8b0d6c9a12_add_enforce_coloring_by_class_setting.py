"""add_enforce_coloring_by_class_setting.

Revision ID: 7e8b0d6c9a12
Revises: dc6fddd82c1c
Create Date: 2026-06-18 09:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7e8b0d6c9a12"
down_revision: Union[str, Sequence[str], None] = "dc6fddd82c1c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "setting",
        sa.Column(
            "enforce_coloring_by_class",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("setting", "enforce_coloring_by_class")
