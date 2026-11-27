"""add evaluation class metric.

Adds the ``evaluation_class_metric`` table. A row stores one per-class summary metric of
an evaluation run, such as the average precision of a class. ``config_override`` holds the
config fields that differ from the run's config, for example the IoU threshold.

Revision ID: e4c3c74ae338
Revises: d5e6f7a8b9c0
Create Date: 2026-10-16 10:04:07.812833

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlmodel.sql.sqltypes import AutoString

# revision identifiers, used by Alembic.
revision: str = "e4c3c74ae338"
down_revision: str | Sequence[str] | None = "d5e6f7a8b9c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "evaluation_class_metric",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evaluation_run_id", sa.Uuid(), nullable=False),
        sa.Column("annotation_label_id", sa.Uuid(), nullable=False),
        sa.Column("metric_name", AutoString(), nullable=False),
        sa.Column(
            "config_override",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("value", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["evaluation_run_id"], ["evaluation_run.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "evaluation_run_id", "annotation_label_id", "metric_name", "config_override"
        ),
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
