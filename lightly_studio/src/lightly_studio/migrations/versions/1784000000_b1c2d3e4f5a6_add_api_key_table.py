"""add-api-key-table.

Revision ID: b1c2d3e4f5a6
Revises: c3d4e5f6a7b8
Create Date: 2026-07-22 14:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "api_key",
        sa.Column("api_key_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("key_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "REVOKED", name="apikeystatus"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("api_key_id"),
    )
    op.create_index("ix_api_key_key_hash", "api_key", ["key_hash"], unique=True)
    op.create_index("ix_api_key_user_id", "api_key", ["user_id"], unique=False)
    op.create_index("ix_api_key_created_at", "api_key", ["created_at"], unique=False)
    op.create_index("ix_api_key_status", "api_key", ["status"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_api_key_status", table_name="api_key")
    op.drop_index("ix_api_key_created_at", table_name="api_key")
    op.drop_index("ix_api_key_user_id", table_name="api_key")
    op.drop_index("ix_api_key_key_hash", table_name="api_key")
    op.drop_table("api_key")
    sa.Enum(name="apikeystatus").drop(op.get_bind(), checkfirst=False)
