"""add mcap table.

Adds the ``mcap`` locator table (1:1 with ``sample``) and the ``MCAP`` value on the
``SampleType`` enum. Rows hold seek keys into an ``.mcap`` file (channel id + log
time), not payload bytes; camera vs. lidar is the ``mcap_data_type`` column.

Revision ID: af51a31f2cd3
Revises: e5f6a7b8c9d0
Create Date: 2026-08-28 16:48:57.097750

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from alembic_postgresql_enum import TableReference
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "af51a31f2cd3"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    sa.Enum("IMAGE", "POINT_CLOUD", name="mcapdatatype").create(op.get_bind())
    op.create_table(
        "mcap",
        sa.Column(
            "mcap_data_type",
            postgresql.ENUM("IMAGE", "POINT_CLOUD", name="mcapdatatype", create_type=False),
            nullable=False,
        ),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("log_time_ns", sa.BigInteger(), nullable=False),
        sa.Column("capture_timestamp_ns", sa.BigInteger(), nullable=False),
        sa.Column("keyframe_log_time_ns", sa.BigInteger(), nullable=True),
        sa.Column("point_count", sa.Integer(), nullable=True),
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["sample_id"],
            ["sample.sample_id"],
        ),
        sa.PrimaryKeyConstraint("sample_id"),
    )
    op.create_index(op.f("ix_mcap_created_at"), "mcap", ["created_at"], unique=False)
    op.sync_enum_values( # type: ignore[attr-defined]
        enum_schema="public",
        enum_name="sampletype",
        new_values=["VIDEO", "VIDEO_FRAME", "IMAGE", "ANNOTATION", "CAPTION", "GROUP", "MCAP"],
        affected_columns=[
            TableReference(
                table_schema="public", table_name="collection", column_name="sample_type"
            )
        ],
        enum_values_to_rename=[],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.sync_enum_values( # type: ignore[attr-defined]
        enum_schema="public",
        enum_name="sampletype",
        new_values=["VIDEO", "VIDEO_FRAME", "IMAGE", "ANNOTATION", "CAPTION", "GROUP"],
        affected_columns=[
            TableReference(
                table_schema="public", table_name="collection", column_name="sample_type"
            )
        ],
        enum_values_to_rename=[],
    )
    op.drop_index(op.f("ix_mcap_created_at"), table_name="mcap")
    op.drop_table("mcap")
    sa.Enum("IMAGE", "POINT_CLOUD", name="mcapdatatype").drop(op.get_bind())
