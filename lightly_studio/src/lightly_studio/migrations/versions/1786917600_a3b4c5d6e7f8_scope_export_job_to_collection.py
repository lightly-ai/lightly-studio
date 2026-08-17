"""scope_export_job_to_collection.

Adds ``export_job.collection_id`` so a download request can be rejected when the
``collection_id`` in the path does not match the collection the export was
prepared for. Existing rows are dropped first: an export job outlives only the
single prepare/download round trip, its ``export_path`` points at a temp
directory, and rows left over from before this migration cannot be attributed
to a collection.

Revision ID: a3b4c5d6e7f8
Revises: b7c8d9e0f1a2
Create Date: 2026-08-17 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3b4c5d6e7f8"
down_revision: Union[str, Sequence[str], None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(sa.text("DELETE FROM export_job"))
    op.add_column("export_job", sa.Column("collection_id", sa.Uuid(), nullable=False))
    op.create_index(
        op.f("ix_export_job_collection_id"), "export_job", ["collection_id"], unique=False
    )
    op.create_foreign_key(
        "fk_export_job_collection_id",
        "export_job",
        "collection",
        ["collection_id"],
        ["collection_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_export_job_collection_id", "export_job", type_="foreignkey")
    op.drop_index(op.f("ix_export_job_collection_id"), table_name="export_job")
    op.drop_column("export_job", "collection_id")
