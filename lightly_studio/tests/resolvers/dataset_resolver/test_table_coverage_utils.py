from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from sqlalchemy import Column, Integer, Table
from sqlmodel import SQLModel

from lightly_studio.resolvers.dataset_resolver import table_coverage_utils


def test_verify_table_coverage() -> None:
    table_coverage_utils.verify_table_coverage()


def test_verify_table_coverage__ignores_table_in_other_schema() -> None:
    with _extra_table(schema="extension"):
        table_coverage_utils.verify_table_coverage()


def test_verify_table_coverage__fails_for_new_table_in_default_schema() -> None:
    with _extra_table(schema=None), pytest.raises(RuntimeError, match="Table count"):
        table_coverage_utils.verify_table_coverage()


@contextmanager
def _extra_table(schema: str | None) -> Iterator[None]:
    # The other tests use SQLModel.metadata to create and truncate the tables, so the extra table
    # must not stay in it.
    table = Table(
        "test_extra_table",
        SQLModel.metadata,
        Column("id", Integer, primary_key=True),
        schema=schema,
    )
    try:
        yield
    finally:
        SQLModel.metadata.remove(table)
