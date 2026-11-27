"""Table coverage verification for collection operations.

This module ensures that deep_copy and delete_dataset handle all database tables.
If new tables are added, these operations will fail with a clear error message
until they are updated to handle the new tables.
"""

from sqlmodel import SQLModel

# Tables handled by deep_copy and delete_dataset.
# - export_job is handled by delete_dataset only (its collection_id FK must be cleared
#   before the collection is deleted); deep_copy intentionally leaves it alone since a job
#   is a transient download token, not data worth duplicating.
# - embedding_plot is deleted with its dataset; copies rebuild plots with their new sample IDs.
_HANDLED_TABLES_COUNT = 40

# Tables not relevant for collection operations:
# - setting (application-level, not collection-specific)
# - user_account (application-level, not collection-specific)
_EXCLUDED_TABLES_COUNT = 2

_TOTAL_TABLES_COUNT = _HANDLED_TABLES_COUNT + _EXCLUDED_TABLES_COUNT


def verify_table_coverage() -> None:
    """Verify that all relevant SQLModel tables are handled.

    This check ensures that when new database tables are added, the deep_copy
    and delete_dataset operations are updated to handle them appropriately.
    The check counts only the tables in the default schema. An application that
    extends LightlyStudio can add its own tables to `SQLModel.metadata` in another
    schema. The application handles those tables, so they do not count.

    Raises:
        RuntimeError: If the number of SQLModel tables in the default schema has changed.
    """
    actual_count = sum(1 for table in SQLModel.metadata.tables.values() if table.schema is None)
    if actual_count != _TOTAL_TABLES_COUNT:
        raise RuntimeError(
            f"Table count in the default schema changed ({actual_count} != {_TOTAL_TABLES_COUNT}). "
            "Update deep_copy and delete_dataset to handle new tables, then update "
            "_HANDLED_TABLES_COUNT or _EXCLUDED_TABLES_COUNT in table_coverage_utils.py."
        )
