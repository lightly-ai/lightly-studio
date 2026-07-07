"""make_evaluation_run_name_unique_per_dataset.

Revision ID: 4687cea2f49d
Revises: dc6fddd82c1c
Create Date: 2026-06-18 11:22:57.374576

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4687cea2f49d"
down_revision: Union[str, Sequence[str], None] = "7e8b0d6c9a12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("evaluation_run", sa.Column("dataset_id", sa.Uuid(), nullable=True))
    op.create_index(
        op.f("ix_evaluation_run_dataset_id"), "evaluation_run", ["dataset_id"], unique=False
    )
    op.execute(
        sa.text(
            """
            UPDATE evaluation_run AS er
            SET dataset_id = c.dataset_id
            FROM collection AS c
            WHERE er.gt_annotation_collection_id = c.collection_id
            """
        )
    )
    op.alter_column("evaluation_run", "dataset_id", nullable=False)
    duplicates = (
        op.get_bind()
        .execute(
            sa.text(
                """
            SELECT name, dataset_id, COUNT(*)
            FROM evaluation_run
            GROUP BY name, dataset_id
            HAVING COUNT(*) > 1
            """
            )
        )
        .fetchall()
    )
    if duplicates:
        raise RuntimeError(
            "Cannot add unique constraint: "
            f"{len(duplicates)} duplicate (name, dataset_id) pairs in evaluation_run. "
            "Resolve before migrating."
        )

    op.create_unique_constraint(
        "uq_evaluation_run_name_dataset_id", "evaluation_run", ["name", "dataset_id"]
    )
    op.create_foreign_key(
        "fk_evaluation_run_dataset_id", "evaluation_run", "dataset", ["dataset_id"], ["dataset_id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_evaluation_run_dataset_id", "evaluation_run", type_="foreignkey")
    op.drop_constraint("uq_evaluation_run_name_dataset_id", "evaluation_run", type_="unique")
    op.drop_index(op.f("ix_evaluation_run_dataset_id"), table_name="evaluation_run")
    op.drop_column("evaluation_run", "dataset_id")
