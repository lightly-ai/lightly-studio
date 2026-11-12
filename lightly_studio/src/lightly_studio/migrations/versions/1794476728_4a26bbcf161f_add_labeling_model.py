"""Add the labeling models on remote servers that a dataset saves."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlmodel.sql.sqltypes import AutoString

revision = "4a26bbcf161f"
down_revision = "8660d246e98e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the labeling_model table."""
    op.create_table(
        "labeling_model",
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("model_id", AutoString(), nullable=False),
        sa.Column("url", AutoString(), nullable=False),
        sa.Column("api_key", AutoString(), nullable=True),
        sa.Column("labeling_model_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["dataset.dataset_id"]),
        sa.PrimaryKeyConstraint("labeling_model_id"),
        sa.UniqueConstraint("dataset_id", "model_id", name="unique_labeling_model_id"),
    )
    op.create_index(
        op.f("ix_labeling_model_created_at"), "labeling_model", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_labeling_model_dataset_id"), "labeling_model", ["dataset_id"], unique=False
    )


def downgrade() -> None:
    """Drop the labeling_model table."""
    op.drop_index(op.f("ix_labeling_model_dataset_id"), table_name="labeling_model")
    op.drop_index(op.f("ix_labeling_model_created_at"), table_name="labeling_model")
    op.drop_table("labeling_model")
