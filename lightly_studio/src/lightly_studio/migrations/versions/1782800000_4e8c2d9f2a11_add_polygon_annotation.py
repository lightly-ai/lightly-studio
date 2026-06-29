"""add_polygon_annotation.

Revision ID: 4e8c2d9f2a11
Revises: 4687cea2f49d
Create Date: 2026-06-29 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from alembic_postgresql_enum import TableReference

# revision identifiers, used by Alembic.
revision: str = "4e8c2d9f2a11"
down_revision: Union[str, Sequence[str], None] = "4687cea2f49d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.sync_enum_values(  # type: ignore[attr-defined]
        enum_schema="public",
        enum_name="annotationtype",
        new_values=["CLASSIFICATION", "SEGMENTATION_MASK", "OBJECT_DETECTION", "POLYGON"],
        affected_columns=[
            TableReference(
                table_schema="public", table_name="annotation_base", column_name="annotation_type"
            )
        ],
        enum_values_to_rename=[],
    )

    op.create_table(
        "polygon_annotation",
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("points", sa.JSON(), nullable=False),
        sa.Column("x", sa.Integer(), nullable=False),
        sa.Column("y", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["sample_id"],
            ["annotation_base.sample_id"],
        ),
        sa.PrimaryKeyConstraint("sample_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("polygon_annotation")
    op.execute("DELETE FROM annotation_base WHERE annotation_type = 'POLYGON'")
    op.sync_enum_values(  # type: ignore[attr-defined]
        enum_schema="public",
        enum_name="annotationtype",
        new_values=["CLASSIFICATION", "SEGMENTATION_MASK", "OBJECT_DETECTION"],
        affected_columns=[
            TableReference(
                table_schema="public", table_name="annotation_base", column_name="annotation_type"
            )
        ],
        enum_values_to_rename=[],
    )
