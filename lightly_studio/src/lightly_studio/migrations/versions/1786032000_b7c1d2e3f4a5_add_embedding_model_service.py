"""add-embedding-model-service.

Revision ID: b7c1d2e3f4a5
Revises: e8f9a0b1c2d3
Create Date: 2026-08-06 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlmodel.sql.sqltypes import AutoString

# revision identifiers, used by Alembic.
revision: str = "b7c1d2e3f4a5"
down_revision: Union[str, Sequence[str], None] = "e8f9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "embedding_model_service",
        sa.Column("embedding_model_hash", sa.VARCHAR(length=128), nullable=False),
        sa.Column("serving_url", AutoString(), nullable=False),
        sa.Column("embedding_model_service_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("embedding_model_service_id"),
    )
    op.create_index(
        op.f("ix_embedding_model_service_embedding_model_hash"),
        "embedding_model_service",
        ["embedding_model_hash"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_embedding_model_service_embedding_model_hash"),
        table_name="embedding_model_service",
    )
    op.drop_table("embedding_model_service")
