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
_HANDLED_TABLES_COUNT = 25

# Tables not relevant for collection operations:
# - setting (application-level, not collection-specific)
# - two_dim_embeddings (cached projections, regenerated as needed)
# - default_embedding_space (excluded here, but the write path has now landed, so it is
#   populated in Postgres — see the TODO below)
# TODO(Michal, 08/2026): default_embedding_space is now written (backfill +
# register_embedding_model), but deep_copy and delete_dataset still ignore it. Until PR2 wires
# them up, on Postgres delete_dataset raises an FK error for any dataset with embeddings (its rows
# still reference embedding_model/collection) and deep_copy silently drops the copied collection's
# default. PR2 must: delete its rows in delete_dataset.py, copy them in deep_copy.py, and move it
# into _HANDLED_TABLES_COUNT. This break is acceptable only because PR1b and PR2 ship together.
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
        "_HANDLED_TABLES_COUNT in table_coverage_utils.py."
    )
