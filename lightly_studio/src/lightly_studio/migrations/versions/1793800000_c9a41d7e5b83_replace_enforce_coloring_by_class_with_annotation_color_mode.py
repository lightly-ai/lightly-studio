"""replace_enforce_coloring_by_class_with_annotation_color_mode.

Revision ID: c9a41d7e5b83
Revises: 8660d246e98e
Create Date: 2026-11-04 10:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9a41d7e5b83"
down_revision: Union[str, Sequence[str], None] = "8660d246e98e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema; every existing row gets the color mode "class"."""
    op.add_column(
        "setting",
        sa.Column(
            "annotation_color_mode",
            sa.String(),
            server_default="class",
            nullable=False,
        ),
    )
    op.drop_column("setting", "enforce_coloring_by_class")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "setting",
        sa.Column(
            "enforce_coloring_by_class",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.execute(
        sa.text("UPDATE setting SET enforce_coloring_by_class = (annotation_color_mode = 'class')")
    )
    op.drop_column("setting", "annotation_color_mode")
