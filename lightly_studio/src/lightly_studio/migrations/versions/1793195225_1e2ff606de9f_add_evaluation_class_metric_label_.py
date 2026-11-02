"""add evaluation class metric label foreign key.

Adds a foreign key and an index from ``evaluation_class_metric.annotation_label_id`` to
``annotation_label``. The upgrade first deletes the class metric rows whose label does not
exist. The foreign key cannot be added while such rows exist, and they carry no information.

Revision ID: 1e2ff606de9f
Revises: b7d24e8f913a
Create Date: 2026-10-28 14:47:05.443600

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1e2ff606de9f"
down_revision: str | Sequence[str] | None = "b7d24e8f913a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        sa.text(
            "DELETE FROM evaluation_class_metric "
            "WHERE annotation_label_id NOT IN (SELECT annotation_label_id FROM annotation_label)"
        )
    )
    op.create_index(
        op.f("ix_evaluation_class_metric_annotation_label_id"),
        "evaluation_class_metric",
        ["annotation_label_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_evaluation_class_metric_annotation_label_id",
        "evaluation_class_metric",
        "annotation_label",
        ["annotation_label_id"],
        ["annotation_label_id"],
    )


def downgrade() -> None:
    """Downgrade schema.

    The class metric rows deleted by the upgrade are not restored.
    """
    op.drop_constraint(
        "fk_evaluation_class_metric_annotation_label_id",
        "evaluation_class_metric",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_evaluation_class_metric_annotation_label_id"),
        table_name="evaluation_class_metric",
    )
