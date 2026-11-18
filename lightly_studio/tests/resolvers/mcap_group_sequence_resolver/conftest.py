"""Fixtures for MCAP group sequence resolver tests."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlmodel import Session

from tests import helpers_workflow


@pytest.fixture
def workflow_tables(db_session: Session) -> Generator[None, None, None]:
    with helpers_workflow.workflow_tables(session=db_session):
        yield
