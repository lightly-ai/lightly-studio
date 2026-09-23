"""scope_export_job_to_collection.

Adds ``export_job.collection_id`` so a download request can be rejected when the
``collection_id`` in the path does not match the collection the export was
prepared for. Existing rows are dropped first: an export job outlives only the
single prepare/download round trip, its ``export_path`` points at a temp
directory, and rows left over from before this migration cannot be attributed
to a collection. Their on-disk artifacts are removed before the rows are
dropped, since deleting the row is the only reference to where they live.

Revision ID: a3b4c5d6e7f8
Revises: b7c8d9e0f1a2
Create Date: 2026-08-17 00:00:00.000000

"""

import shutil
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3b4c5d6e7f8"
down_revision: Union[str, Sequence[str], None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _remove_existing_export_artifacts() -> None:
    """Remove the on-disk artifact of every existing export job.

    Every ``export_path`` is generated under the system temp directory (see
    ``lightly_studio.api.routes.api.export``); paths outside of it are left untouched rather
    than removed, since they cannot be confirmed to be export-owned.
    """
    connection = op.get_bind()
    export_paths = connection.execute(sa.text("SELECT export_path FROM export_job")).scalars()
    temp_dir = Path(tempfile.gettempdir()).resolve()
    for export_path in export_paths:
        resolved_path = Path(export_path).resolve()
        try:
            relative_path = resolved_path.relative_to(temp_dir)
        except ValueError:
            continue
        if relative_path == Path():
            # Equality is not raised by `relative_to`; reject the temp directory root itself.
            continue
        if resolved_path.is_dir():
            shutil.rmtree(resolved_path, ignore_errors=True)
        else:
            resolved_path.unlink(missing_ok=True)


def upgrade() -> None:
    """Upgrade schema."""
    _remove_existing_export_artifacts()
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
