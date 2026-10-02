"""add evaluation class metric.

Adds the ``evaluation_class_metric`` table. A row stores one per-class summary metric of
an evaluation run, such as the average precision of a class at one IoU threshold.

Revision ID: 2d93787be69f
Revises: e1f2a3b4c5d6
Create Date: 2026-09-30 20:11:26.668092

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlmodel.sql.sqltypes import AutoString

# revision identifiers, used by Alembic.
revision: str = "2d93787be69f"
down_revision: str | Sequence[str] | None = "e1f2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "evaluation_class_metric",
        sa.Column("evaluation_run_id", sa.Uuid(), nullable=False),
        sa.Column("annotation_label_id", sa.Uuid(), nullable=False),
        sa.Column("metric_name", AutoString(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["evaluation_run_id"],
            ["evaluation_run.id"],
        ),
        sa.PrimaryKeyConstraint("evaluation_run_id", "annotation_label_id", "metric_name"),
    )
    op.create_index(
        op.f("ix_evaluation_class_metric_evaluation_run_id"),
        "evaluation_class_metric",
        ["evaluation_run_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_evaluation_class_metric_evaluation_run_id"),
        table_name="evaluation_class_metric",
    )
    op.drop_table("evaluation_class_metric")
