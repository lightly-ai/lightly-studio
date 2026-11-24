"""add_evaluation_run_sample_scope.

Adds the nullable ``sample_scope_json`` column to ``evaluation_run``. It stores the
collection and image filter that select the images of a run, so a recompute keeps them.

Revision ID: d682b223845d
Revises: 37ee066f0639
Create Date: 2026-11-24 17:06:05.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d682b223845d"
down_revision: str | Sequence[str] | None = "37ee066f0639"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("evaluation_run", sa.Column("sample_scope_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("evaluation_run", "sample_scope_json")
