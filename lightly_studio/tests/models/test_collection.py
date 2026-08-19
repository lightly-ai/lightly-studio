"""Tests for the Collection model constraints."""

from __future__ import annotations

import pytest
import sqlalchemy
from sqlmodel import Session

from lightly_studio.models.collection import CollectionTable, SampleType
from tests.helpers_resolvers import create_collection


@pytest.mark.postgres_only  # The partial unique index only exists on Postgres.
def test_collection_table__root_duplicate_name_rejected_by_database(db_session: Session) -> None:
    """A second root collection with an existing name fails at the database level.

    Bypasses `collection_resolver.create`'s application-level duplicate check, which
    would otherwise reject the duplicate before it reaches the database.
    """
    root = create_collection(session=db_session, collection_name="duplicate_root")

    db_session.add(
        CollectionTable(
            name=root.name,
            parent_collection_id=None,
            sample_type=SampleType.IMAGE,
            dataset_id=root.dataset_id,
        )
    )
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db_session.commit()
    # The failed commit leaves the session pending a rollback, without it the fixture
    # teardown fails when it commits the session.
    db_session.rollback()
