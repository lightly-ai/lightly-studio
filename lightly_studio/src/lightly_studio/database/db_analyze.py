"""Refresh database planner statistics so index scans are chosen on bulk loads.

A freshly created and bulk-inserted collection has no ``pg_statistic`` row for its
new ``collection_id``. PostgreSQL then estimates the collection at ~1 row and
prefers a collection scan over the selective ``file_path_abs`` index probe, which
makes the per-batch dedup query in the image loaders O(N) and the whole load
O(N²). Running ``ANALYZE`` once the collection holds a representative number of
rows flips the planner to the index scan and it stays correct as the collection
grows.

DuckDB maintains its own statistics automatically, so these helpers are a no-op
on non-PostgreSQL backends.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import text
from sqlmodel import Session

# Rows to insert before the first ANALYZE during a bulk load. Kept small so the
# first refresh fires early (once the table clearly exceeds the dedup IN-list size),
# which is the refresh that flips the PostgreSQL planner onto the file_path_abs index.
DEFAULT_INITIAL_ROWS = 1_000
# Upper bound on the gap between ANALYZE runs. The interval doubles after each run,
# so refreshes stay rare on large loads (~log N total).
DEFAULT_MAX_INTERVAL_ROWS = 250_000


def analyze_tables(session: Session, table_names: Sequence[str]) -> None:
    """Run ``ANALYZE`` on ``table_names`` to refresh PostgreSQL planner statistics.

    No-op on non-PostgreSQL backends. Commits so the refreshed statistics are
    visible to subsequent queries on the same session.

    ``ANALYZE`` is transaction-safe (unlike ``VACUUM``) and takes only a lightweight
    ``SHARE UPDATE EXCLUSIVE`` lock, so it does not block concurrent reads or writes.

    Args:
        session: The database session.
        table_names: Trusted, internal table names to analyze (not user input).
    """
    if not table_names:
        return
    bind = session.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return
    session.execute(text(f"ANALYZE {', '.join(table_names)}"))
    session.commit()


class PlannerStatsRefresher:
    """Triggers ``ANALYZE`` periodically during a bulk load to keep query plans fast.

    A per-batch dedup query only uses a column index if PostgreSQL has statistics
    for the freshly created collection. This refresher runs ``ANALYZE`` after the
    first ``initial_rows`` inserted rows and then on a doubling interval (capped at
    ``max_interval_rows``), so the critical first refresh happens early while later
    refreshes stay rare. No-op on DuckDB (see ``analyze_tables``).
    """

    def __init__(
        self,
        table_names: Sequence[str],
        initial_rows: int = DEFAULT_INITIAL_ROWS,
        max_interval_rows: int = DEFAULT_MAX_INTERVAL_ROWS,
    ) -> None:
        """Initialize the refresher for ``table_names`` with the given row thresholds."""
        self._table_names = list(table_names)
        self._max_interval_rows = max_interval_rows
        self._rows_since_analyze = 0
        self._next_threshold = initial_rows

    def record(self, session: Session, n_new_rows: int) -> None:
        """Record newly inserted rows and run ``ANALYZE`` once the threshold is hit."""
        self._rows_since_analyze += n_new_rows
        if self._rows_since_analyze >= self._next_threshold:
            analyze_tables(session=session, table_names=self._table_names)
            self._rows_since_analyze = 0
            self._next_threshold = min(self._next_threshold * 2, self._max_interval_rows)
