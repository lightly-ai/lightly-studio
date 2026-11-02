"""Mark workspace-managed object tracks and bind them to a sequence."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "81fa9b774c20"
down_revision = "b7d24e8f913a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add explicit management and sequence scope without converting existing tracks."""
    op.add_column(
        "object_track",
        sa.Column("managed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("object_track", sa.Column("sequence_sample_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_object_track_sequence_sample_id",
        "object_track",
        "sequence",
        ["sequence_sample_id"],
        ["sample_id"],
    )


def downgrade() -> None:
    """Remove managed-track metadata."""
    op.drop_constraint("fk_object_track_sequence_sample_id", "object_track", type_="foreignkey")
    op.drop_column("object_track", "sequence_sample_id")
    op.drop_column("object_track", "managed")
