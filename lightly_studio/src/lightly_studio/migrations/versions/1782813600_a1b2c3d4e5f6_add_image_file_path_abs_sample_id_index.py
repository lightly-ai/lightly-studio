"""add_image_file_path_abs_sample_id_index.

Adds a composite index on ``image(file_path_abs, sample_id)`` to support keyset
(seek) pagination for the sample-adjacents endpoint. The previous implementation
computed ``lag``/``lead``/``row_number`` window functions over the entire
collection on every prev/next click, forcing a full sort/scan. The keyset
rewrite seeks the next/previous row using this index instead.

Revision ID: a1b2c3d4e5f6
Revises: 4687cea2f49d
Create Date: 2026-06-30 10:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "4687cea2f49d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        op.f("ix_image_file_path_abs_sample_id"),
        "image",
        ["file_path_abs", "sample_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_image_file_path_abs_sample_id"), table_name="image")
