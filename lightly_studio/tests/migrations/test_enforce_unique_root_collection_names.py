from __future__ import annotations

import importlib
from datetime import timedelta

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session, select

from lightly_studio.models.collection import CollectionTable, SampleType
from tests.helpers_resolvers import create_collection

_migration = importlib.import_module(
    "lightly_studio.migrations.versions."
    "1787011200_4f6a7b8c9d0e_enforce_unique_root_collection_names"
)


# Postgres builds its schema from the migrations, so the index is already in place there
# and the duplicates this test needs cannot be inserted. The rename SQL is plain ANSI.
@pytest.mark.duckdb_only
def test_rename_duplicate_root_collections(db_session: Session, mocker: MockerFixture) -> None:
    # Builds the pre-migration state, bypassing `collection_resolver.create` which
    # rejects duplicate names before they reach the database.
    oldest = create_collection(session=db_session, collection_name="ds")
    create_collection(session=db_session, collection_name="ds (2)")
    duplicates = [
        CollectionTable(
            name="ds",
            parent_collection_id=None,
            sample_type=SampleType.IMAGE,
            dataset_id=oldest.dataset_id,
            created_at=oldest.created_at + timedelta(days=days),
        )
        for days in (1, 2)
    ]
    db_session.add_all(duplicates)
    db_session.commit()
    mocker.patch.object(_migration.op, "get_bind", return_value=db_session.connection())

    _migration._rename_duplicate_root_collections()

    db_session.expire_all()
    names = dict(db_session.exec(select(CollectionTable.collection_id, CollectionTable.name)).all())
    # The oldest collection keeps the name. ` (2)` belongs to an unrelated dataset, so the
    # duplicates take the next free suffixes in creation order.
    assert names[oldest.collection_id] == "ds"
    assert names[duplicates[0].collection_id] == "ds (3)"
    assert names[duplicates[1].collection_id] == "ds (4)"
