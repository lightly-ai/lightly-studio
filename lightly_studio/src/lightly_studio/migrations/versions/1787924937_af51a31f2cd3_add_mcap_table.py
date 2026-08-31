"""add mcap table.

Adds the ``mcap`` locator table (1:1 with ``sample``) and the ``MCAP`` value on the
``SampleType`` enum. Rows hold seek keys into an ``.mcap`` file (channel id + log
time), not payload bytes.

Revision ID: af51a31f2cd3
Revises: d1e2f3a4b5c6
Create Date: 2026-08-28 16:48:57.097750

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from alembic_postgresql_enum import TableReference

# revision identifiers, used by Alembic.
revision: str = "af51a31f2cd3"
down_revision: Union[str, Sequence[str], None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "mcap",
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
    op.sync_enum_values(  # type: ignore[attr-defined]
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
    mcap_collections = (
        op.get_bind()
        .execute(sa.text("SELECT COUNT(*) FROM collection WHERE sample_type = 'MCAP'"))
        .scalar()
    )
    if mcap_collections:
        raise RuntimeError(
            "Cannot remove MCAP from sampletype enum: "
            f"{mcap_collections} collection(s) still have sample_type = 'MCAP'. "
            "Remove or remap those collections before downgrading."
        )

    op.sync_enum_values(  # type: ignore[attr-defined]
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
