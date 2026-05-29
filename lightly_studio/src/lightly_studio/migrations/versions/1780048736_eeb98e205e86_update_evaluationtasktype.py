"""update-EvaluationTaskType.

Revision ID: eeb98e205e86
Revises: fa45898e4138
Create Date: 2026-05-29 12:58:56.227096

"""

from collections.abc import Sequence
from typing import Union

from alembic import op
from alembic_postgresql_enum import TableReference

# revision identifiers, used by Alembic.
revision: str = "eeb98e205e86"
down_revision: Union[str, Sequence[str], None] = "fa45898e4138"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.sync_enum_values(  # type: ignore[attr-defined]
        enum_schema="public",
        enum_name="evaluationtasktype",
        new_values=[
            "OBJECT_DETECTION",
            "CLASSIFICATION",
            "INSTANCE_SEGMENTATION",
            "SEMANTIC_SEGMENTATION",
        ],
        affected_columns=[
            TableReference(
                table_schema="public", table_name="evaluation_run", column_name="task_type"
            )
        ],
        enum_values_to_rename=[],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.sync_enum_values(  # type: ignore[attr-defined]
        enum_schema="public",
        enum_name="evaluationtasktype",
        new_values=["OBJECT_DETECTION", "CLASSIFICATION", "INSTANCE_SEGMENTATION"],
        affected_columns=[
            TableReference(
                table_schema="public", table_name="evaluation_run", column_name="task_type"
            )
        ],
        enum_values_to_rename=[],
    )
