from __future__ import annotations

import importlib

from pytest_mock import MockerFixture
from sqlmodel import Session, select

from lightly_studio.models.collection import CollectionTable, SampleType
from tests.helpers_resolvers import create_collection

_migration = importlib.import_module(
    "lightly_studio.migrations.versions."
    "1787011200_4f6a7b8c9d0e_enforce_unique_root_collection_names"
)


def test_rename_duplicate_root_collections(db_session: Session, mocker: MockerFixture) -> None:
    # Builds the pre-migration state, bypassing `collection_resolver.create` which
    # rejects duplicate names before they reach the database.
    root = create_collection(session=db_session, collection_name="ds")
    create_collection(session=db_session, collection_name="ds (2)")
    for _ in range(2):
        db_session.add(
            CollectionTable(
                name="ds",
                parent_collection_id=None,
                sample_type=SampleType.IMAGE,
                dataset_id=root.dataset_id,
            )
        )
    db_session.commit()
    mocker.patch.object(_migration.op, "get_bind", return_value=db_session.connection())

    _migration._rename_duplicate_root_collections()

    db_session.expire_all()
    names = sorted(db_session.exec(select(CollectionTable.name)).all())
    # The oldest collection keeps the name, ` (2)` is taken by an unrelated dataset.
    assert names == ["ds", "ds (2)", "ds (3)", "ds (4)"]
