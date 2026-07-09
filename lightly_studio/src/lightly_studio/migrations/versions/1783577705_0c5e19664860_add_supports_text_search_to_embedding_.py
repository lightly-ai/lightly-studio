"""add_supports_text_search_to_embedding_model.

Revision ID: 0c5e19664860
Revises: a1b2c3d4e5f6
Create Date: 2026-07-09 10:15:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0c5e19664860"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Defaults to true because all rows created before this column existed came
    # from CLIP-style vision-text generators.
    op.add_column(
        "embedding_model",
        sa.Column(
            "supports_text_search",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("embedding_model", "supports_text_search")
