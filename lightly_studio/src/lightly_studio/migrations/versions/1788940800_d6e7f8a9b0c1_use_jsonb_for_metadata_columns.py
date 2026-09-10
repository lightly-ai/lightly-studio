"""use jsonb for the metadata data and metadata_schema columns.

Converts ``metadata.data`` and ``metadata.metadata_schema`` from ``json`` to ``jsonb`` so metadata
filters, histograms, and value counts operate on parsed binary JSON instead of re-parsing text on
every access. The ``->``/``->>`` extraction operators behave the same on ``json`` and ``jsonb``,
so the metadata query SQL is unchanged.

``jsonb`` normalizes stored values: object key order is not preserved, duplicate keys collapse to
the last value, and insignificant whitespace and number formatting are normalized. It also applies
stricter Unicode and numeric acceptance rules than ``json``. The downgrade restores ``json``
storage, not the original textual formatting.

DuckDB builds its schema with ``create_all`` and has no ``jsonb`` type, so this migration only
matters for tracked Postgres databases; DuckDB keeps the generic ``json`` type.

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-09-10 08:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d6e7f8a9b0c1"
down_revision: str | Sequence[str] | None = "c5d6e7f8a9b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "metadata",
        "data",
        type_=postgresql.JSONB(),
        existing_type=sa.JSON(),
        existing_nullable=False,
        postgresql_using="data::jsonb",
    )
    op.alter_column(
        "metadata",
        "metadata_schema",
        type_=postgresql.JSONB(),
        existing_type=sa.JSON(),
        existing_nullable=False,
        postgresql_using="metadata_schema::jsonb",
    )


def downgrade() -> None:
    """Downgrade schema.

    Restores ``json`` storage. The stored values are preserved semantically, but the original
    textual formatting and key order are not recovered.
    """
    op.alter_column(
        "metadata",
        "data",
        type_=sa.JSON(),
        existing_type=postgresql.JSONB(),
        existing_nullable=False,
        postgresql_using="data::json",
    )
    op.alter_column(
        "metadata",
        "metadata_schema",
        type_=sa.JSON(),
        existing_type=postgresql.JSONB(),
        existing_nullable=False,
        postgresql_using="metadata_schema::json",
    )
