"""Tests for the db_analyze module."""

from __future__ import annotations

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.database import db_analyze
from lightly_studio.database.db_analyze import PlannerStatsRefresher


def test_analyze_tables__noop_on_duckdb(db_session: Session) -> None:
    """On DuckDB the helper is a no-op and must not raise."""
    db_analyze.analyze_tables(session=db_session, table_names=["sample", "image"])


def test_analyze_tables__empty_table_names_is_noop(db_session: Session) -> None:
    """Empty table list does nothing and does not raise."""
    db_analyze.analyze_tables(session=db_session, table_names=[])


@pytest.mark.postgres_only
def test_analyze_tables__runs_on_postgres(db_session: Session) -> None:
    """On PostgreSQL the ANALYZE statement executes without error."""
    db_analyze.analyze_tables(session=db_session, table_names=["sample", "image"])


def test_planner_stats_refresher__triggers_analyze_on_threshold(
    db_session: Session, mocker: MockerFixture
) -> None:
    """ANALYZE fires once the initial row threshold is crossed, then on a doubling interval."""
    analyze_mock = mocker.patch.object(db_analyze, "analyze_tables")
    refresher = PlannerStatsRefresher(table_names=["sample", "image"])

    # Below the initial threshold: no ANALYZE yet.
    refresher.record(session=db_session, n_new_rows=db_analyze.DEFAULT_INITIAL_ROWS - 1)
    assert analyze_mock.call_count == 0

    # Crossing the initial threshold triggers exactly one ANALYZE on the given tables.
    refresher.record(session=db_session, n_new_rows=1)
    assert analyze_mock.call_count == 1
    assert analyze_mock.call_args.kwargs["table_names"] == ["sample", "image"]

    # The interval doubled, so it now takes 2 * DEFAULT_INITIAL_ROWS rows for the next ANALYZE.
    refresher.record(session=db_session, n_new_rows=2 * db_analyze.DEFAULT_INITIAL_ROWS - 1)
    assert analyze_mock.call_count == 1
    refresher.record(session=db_session, n_new_rows=1)
    assert analyze_mock.call_count == 2


def test_planner_stats_refresher__interval_is_capped(
    db_session: Session, mocker: MockerFixture
) -> None:
    """The doubling interval never grows past max_interval_rows."""
    mocker.patch.object(db_analyze, "analyze_tables")
    refresher = PlannerStatsRefresher(table_names=["sample", "image"])

    # Force many doublings; each record at the cap triggers an ANALYZE and grows the interval.
    for _ in range(20):
        refresher.record(session=db_session, n_new_rows=db_analyze.DEFAULT_MAX_INTERVAL_ROWS)

    assert refresher._next_threshold == db_analyze.DEFAULT_MAX_INTERVAL_ROWS
