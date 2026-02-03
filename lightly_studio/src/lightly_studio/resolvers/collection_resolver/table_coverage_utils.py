"""Table coverage verification for collection operations.

This module ensures that deep_copy and delete_dataset handle all database tables.
If new tables are added, these operations will fail with a clear error message
until they are updated to handle the new tables.
"""

from sqlmodel import SQLModel

# Tables handled by deep_copy and delete_dataset.
_HANDLED_TABLES_COUNT = 17

# Tables not relevant for collection operations:
# - embedding_model (shared resource, not copied/deleted with collections)
# - setting (application-level, not collection-specific)
# - two_dim_embeddings (cached projections, regenerated as needed)
_EXCLUDED_TABLES_COUNT = 3

_TOTAL_TABLES_COUNT = _HANDLED_TABLES_COUNT + _EXCLUDED_TABLES_COUNT


def verify_table_coverage() -> None:
    """Verify that all relevant SQLModel tables are handled.

    This check ensures that when new database tables are added, the deep_copy
    and delete_dataset operations are updated to handle them appropriately.

    Raises:
        AssertionError: If the number of SQLModel tables has changed.
    """
    actual_count = len(SQLModel.metadata.tables)
    assert actual_count == _TOTAL_TABLES_COUNT, (
        f"Table count changed ({actual_count} != {_TOTAL_TABLES_COUNT}). "
        "Update deep_copy and delete_dataset to handle new tables, then update "
        "_HANDLED_TABLES_COUNT in _table_coverage.py."
    )
