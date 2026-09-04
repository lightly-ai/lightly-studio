"""add sequence and sample_sequence_link tables.

Adds the ``sequence`` table (1:1 with ``sample``, keyed by ``sample_id`` like ``group``),
the ``sample_sequence_link`` table that orders samples inside a sequence, and the
``SEQUENCE`` value on the ``SampleType`` enum.

``sample_sequence_link.sample_id`` is the primary key, so a sample sits in at most one
slot of at most one sequence, and ``unique_seq_number_per_sequence`` keeps two samples
from sharing a position in the same sequence. ``timestamp_ns`` is a ``BIGINT`` because
epoch nanoseconds overflow a 32-bit ``INTEGER``.

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-09-02 12:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from alembic_postgresql_enum import TableReference

# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7a8"
down_revision: str | Sequence[str] | None = "a2b3c4d5e6f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SAMPLE_TYPE_COLUMNS = [
    TableReference(table_schema="public", table_name="collection", column_name="sample_type")
]


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "sequence",
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["sample_id"],
            ["sample.sample_id"],
        ),
        sa.PrimaryKeyConstraint("sample_id"),
    )
    op.create_table(
        "sample_sequence_link",
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_id", sa.Uuid(), nullable=False),
        sa.Column("seq_number", sa.Integer(), nullable=False),
        sa.Column("timestamp_ns", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(
            ["sample_id"],
            ["sample.sample_id"],
        ),
        sa.ForeignKeyConstraint(
            ["sequence_id"],
            ["sequence.sample_id"],
        ),
        sa.PrimaryKeyConstraint("sample_id"),
        sa.UniqueConstraint("sequence_id", "seq_number", name="unique_seq_number_per_sequence"),
    )
    op.create_index(
        op.f("ix_sample_sequence_link_sequence_id"),
        "sample_sequence_link",
        ["sequence_id"],
        unique=False,
    )
    op.sync_enum_values(  # type: ignore[attr-defined]
        enum_schema="public",
        enum_name="sampletype",
        new_values=[
            "VIDEO",
            "VIDEO_FRAME",
            "IMAGE",
            "ANNOTATION",
            "CAPTION",
            "GROUP",
            "MCAP",
            "SEQUENCE",
        ],
        affected_columns=_SAMPLE_TYPE_COLUMNS,
        enum_values_to_rename=[],
    )


def downgrade() -> None:
    """Downgrade schema."""
    sequence_collections = (
        op.get_bind()
        .execute(sa.text("SELECT COUNT(*) FROM collection WHERE sample_type = 'SEQUENCE'"))
        .scalar()
    )
    if sequence_collections:
        raise RuntimeError(
            "Cannot remove SEQUENCE from sampletype enum: "
            f"{sequence_collections} collection(s) still have sample_type = 'SEQUENCE'. "
            "Remove or remap those collections before downgrading."
        )

    op.sync_enum_values(  # type: ignore[attr-defined]
        enum_schema="public",
        enum_name="sampletype",
        new_values=["VIDEO", "VIDEO_FRAME", "IMAGE", "ANNOTATION", "CAPTION", "GROUP", "MCAP"],
        affected_columns=_SAMPLE_TYPE_COLUMNS,
        enum_values_to_rename=[],
    )
    op.drop_index(
        op.f("ix_sample_sequence_link_sequence_id"), table_name="sample_sequence_link"
    )
    op.drop_table("sample_sequence_link")
    op.drop_table("sequence")
