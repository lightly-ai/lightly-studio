"""add polygon annotation.

Revision ID: 37ee066f0639
Revises: 1e2ff606de9f
Create Date: 2026-11-23 10:46:23.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from alembic_postgresql_enum import TableReference

# revision identifiers, used by Alembic.
revision: str = "37ee066f0639"
down_revision: str | Sequence[str] | None = "1e2ff606de9f"
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
            "POLYGON",
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
    op.create_table(
        "polygon_annotation",
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("x", sa.Integer(), nullable=False),
        sa.Column("y", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("polygons", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["sample_id"], ["annotation_base.sample_id"]),
        sa.PrimaryKeyConstraint("sample_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM polygon_annotation")
    op.execute("DELETE FROM annotation_base WHERE annotation_type = 'POLYGON'")
    op.drop_table("polygon_annotation")
    op.sync_enum_values(  # type: ignore[attr-defined]
        enum_schema="public",
        enum_name="annotationtype",
        new_values=["CLASSIFICATION", "SEGMENTATION_MASK", "OBJECT_DETECTION", "CUBOID_3D"],
        affected_columns=[
            TableReference(
                table_schema="public",
                table_name="annotation_base",
                column_name="annotation_type",
            )
        ],
        enum_values_to_rename=[],
    )
