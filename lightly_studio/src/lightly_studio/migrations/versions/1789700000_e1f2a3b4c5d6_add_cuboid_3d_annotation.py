"""add cuboid_3d_annotation and object_track parent/source ids.

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-09-22 17:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from alembic_postgresql_enum import TableReference

# revision identifiers, used by Alembic.
revision: str = "e1f2a3b4c5d6"
down_revision: str | Sequence[str] | None = "d0e1f2a3b4c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.sync_enum_values(  # type: ignore[attr-defined]
        enum_schema="public",
        enum_name="annotationtype",
        new_values=[
            "CLASSIFICATION",
            "SEGMENTATION_MASK",
            "OBJECT_DETECTION",
            "CUBOID_3D",
        ],
        affected_columns=[
            TableReference(
                table_schema="public",
                table_name="annotation_base",
                column_name="annotation_type",
            )
        ],
        enum_values_to_rename=[],
    )
    op.add_column("object_track", sa.Column("source_track_id", sa.Integer(), nullable=True))
    op.add_column("object_track", sa.Column("parent_object_track_id", sa.Uuid(), nullable=True))
    op.create_index(
        op.f("ix_object_track_parent_object_track_id"),
        "object_track",
        ["parent_object_track_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_object_track_parent_object_track_id",
        "object_track",
        "object_track",
        ["parent_object_track_id"],
        ["object_track_id"],
    )
    op.create_table(
        "cuboid_3d_annotation",
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("frame_id", sa.String(), nullable=False),
        sa.Column("px", sa.Float(), nullable=False),
        sa.Column("py", sa.Float(), nullable=False),
        sa.Column("pz", sa.Float(), nullable=False),
        sa.Column("qx", sa.Float(), nullable=False),
        sa.Column("qy", sa.Float(), nullable=False),
        sa.Column("qz", sa.Float(), nullable=False),
        sa.Column("qw", sa.Float(), nullable=False),
        sa.Column("sx", sa.Float(), nullable=False),
        sa.Column("sy", sa.Float(), nullable=False),
        sa.Column("sz", sa.Float(), nullable=False),
        sa.Column("interpolated", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["sample_id"], ["annotation_base.sample_id"]),
        sa.PrimaryKeyConstraint("sample_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM cuboid_3d_annotation")
    op.execute("DELETE FROM annotation_base WHERE annotation_type = 'CUBOID_3D'")
    op.drop_table("cuboid_3d_annotation")
    op.drop_constraint("fk_object_track_parent_object_track_id", "object_track", type_="foreignkey")
    op.drop_index(op.f("ix_object_track_parent_object_track_id"), table_name="object_track")
    op.drop_column("object_track", "parent_object_track_id")
    op.drop_column("object_track", "source_track_id")
    op.sync_enum_values(  # type: ignore[attr-defined]
        enum_schema="public",
        enum_name="annotationtype",
        new_values=["CLASSIFICATION", "SEGMENTATION_MASK", "OBJECT_DETECTION"],
        affected_columns=[
            TableReference(
                table_schema="public",
                table_name="annotation_base",
                column_name="annotation_type",
            )
        ],
        enum_values_to_rename=[],
    )
