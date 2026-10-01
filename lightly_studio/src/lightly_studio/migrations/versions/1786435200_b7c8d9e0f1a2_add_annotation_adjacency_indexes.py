"""add_annotation_adjacency_indexes.

Adds the two composite indexes the keyset (seek) path for annotation prev/next needs:

- ``annotation_base(parent_sample_id, created_at, sample_id)`` — the sort keys that live on
  the annotation itself, so each parent's annotations can be read already ordered.
- ``video(file_path_abs, sample_id)`` — the leading sort key for annotations on video
  frames, mirroring the existing ``image(file_path_abs, sample_id)`` index.

The previous implementation sorted the whole filtered annotation set and read the
neighbours off it with ``lag``/``lead``/``row_number`` on every prev/next click. Measured
on PostgreSQL with 4M annotations, that took ~5.9s; the keyset seek these indexes support
brings the neighbour lookup down to ~1ms.

Note that migrations only run on PostgreSQL. DuckDB builds its schema from the models via
``create_all``, so new DuckDB databases pick these indexes up automatically but existing
DuckDB files do not gain them.

Revision ID: b7c8d9e0f1a2
Revises: e8f9a0b1c2d3
Create Date: 2026-08-12 14:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "e8f9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        op.f("ix_annotation_base_parent_sample_id_created_at_sample_id"),
        "annotation_base",
        ["parent_sample_id", "created_at", "sample_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_video_file_path_abs_sample_id"),
        "video",
        ["file_path_abs", "sample_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_video_file_path_abs_sample_id"), table_name="video")
    op.drop_index(
        op.f("ix_annotation_base_parent_sample_id_created_at_sample_id"),
        table_name="annotation_base",
    )
