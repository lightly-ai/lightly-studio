# TODO(Michal, 09/2025): Add tests for:
# - DatabaseEngine
# - session
# - persistent_session

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy
import sqlmodel
from pytest_mock import MockerFixture
from sqlmodel import SQLModel

from lightly_studio import ImageDataset, db_manager
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.order_by import OrderByField
from lightly_studio.db_manager import (
    DatabaseBackend,
    DatabaseEngine,
    _detect_backend_from_url,
)
from lightly_studio.models.collection import CollectionTable
from lightly_studio.resolvers import image_resolver
from tests.helpers_resolvers import (
    create_collection,
    create_image,
)


@pytest.fixture
def patch_engine_singleton(mocker: MockerFixture) -> None:
    """Patch the _engine variable to None before each test.

    This simulates a fresh load of the module.
    """
    mocker.patch.object(db_manager, "_engine", new=None)


def test_get_engine__default(
    mocker: MockerFixture,
    patch_engine_singleton: None,  # noqa ARG001
) -> None:
    """Test get_engine and set_engine functions."""
    # Mock the class DatabaseEngine to avoid creating a real database file in the
    # current working directory.
    mock_engine_class = mocker.patch.object(db_manager, "DatabaseEngine", spec_set=DatabaseEngine)
    mock_engine = mock_engine_class.return_value

    # Act
    engine = db_manager.get_engine()

    # Assert
    assert engine is mock_engine
    mock_engine_class.assert_called_once_with()

    # Get the engine again, should return the same instance.
    engine2 = db_manager.get_engine()
    assert engine2 is mock_engine


def test_set_engine__file_db(
    tmp_path: Path,
    patch_engine_singleton: None,  # noqa ARG001
) -> None:
    """Test set_engine function."""
    engine_url = f"duckdb:///{tmp_path / 'test.db'}"
    engine = DatabaseEngine(engine_url=engine_url, single_threaded=True)
    db_manager.set_engine(engine=engine)

    fetched_engine = db_manager.get_engine()
    assert fetched_engine is engine
    assert fetched_engine._engine_url == engine_url


def test_set_engine__memory_db(
    patch_engine_singleton: None,  # noqa ARG001
) -> None:
    """Test set_engine function."""
    engine_url = "duckdb:///:memory:"
    engine = DatabaseEngine(engine_url=engine_url, single_threaded=True)
    db_manager.set_engine(engine=engine)

    fetched_engine = db_manager.get_engine()
    assert fetched_engine is engine
    assert fetched_engine._engine_url == engine_url


def test_set_engine__raises_if_already_set(
    patch_engine_singleton: None,  # noqa ARG001
) -> None:
    """Test set_engine raises if the engine is already set."""
    engine_url = "duckdb:///:memory:"
    db_manager.set_engine(engine=DatabaseEngine(engine_url=engine_url, single_threaded=True))
    with pytest.raises(
        RuntimeError, match=r"Database engine is already set and cannot be changed."
    ):
        db_manager.set_engine(
            engine=DatabaseEngine(engine_url="duckdb:///:memory:", single_threaded=True)
        )


def test_connect(
    tmp_path: Path,
    patch_engine_singleton: None,  # noqa ARG001
) -> None:
    """Test connect function with a file database."""
    db_file = tmp_path / "test.db"
    db_manager.connect(db_file=str(db_file), cleanup_existing=True)

    engine = db_manager.get_engine()
    assert engine._engine_url == f"duckdb:///{db_file}"

    # Cannot connect again, should raise.
    with pytest.raises(
        RuntimeError, match=r"Database engine is already set and cannot be changed."
    ):
        db_manager.connect(db_file=str(db_file), cleanup_existing=True)


def test_connect__db_file_none(
    mocker: MockerFixture,
    patch_engine_singleton: None,  # noqa ARG001
) -> None:
    """Test connect function with db_file=None."""
    # Mock the class DatabaseEngine to avoid creating a real database file in the
    # current working directory.
    mock_engine_class = mocker.patch.object(db_manager, "DatabaseEngine", spec_set=DatabaseEngine)
    mock_engine = mock_engine_class.return_value

    db_manager.connect(db_file=None, cleanup_existing=True)

    engine = db_manager.get_engine()
    assert engine is mock_engine
    mock_engine_class.assert_called_once_with(
        engine_url=None,
        cleanup_existing=True,
    )


def test_session_data_consistency(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test that verifies data consistency across persistent and short-lived database sessions.

    This test ensures that:
     Data created in one session is visible in subsequent sessions.
     Session management doesn't cause data loss or inconsistency.
    """
    # Patch the db_manager to use a custom test database.
    mocker.patch.object(
        db_manager,
        "get_engine",
        return_value=db_manager.DatabaseEngine(f"duckdb:///{tmp_path}/test.db"),
    )
    # Arrange: Create initial dataset and sample using short-lived database session.
    with db_manager.session() as session:
        dataset_id = create_collection(
            session=session, collection_name="test_session_dataset"
        ).collection_id
        create_image(
            session=session,
            collection_id=dataset_id,
            file_path_abs="image.png",
        )
        # Session commits automatically when exiting the context manager

    dataset = ImageDataset.load(name="test_session_dataset")

    # Verify the Dataset API can see the data created via database session.
    # It uses the persistent session.
    samples = dataset.query().to_list()
    assert len(samples) == 1
    assert samples[0].file_path_abs == "image.png"

    # Create another sample and verify cross-session data visibility
    with db_manager.session() as session:
        create_image(
            session=session,
            collection_id=dataset.dataset_id,
            file_path_abs="image2.png",
        )
        samples_from_resolver = image_resolver.get_all_by_collection_id(
            session=session, collection_id=dataset.dataset_id
        ).samples
        assert len(samples_from_resolver) == 2

    # Verify the Dataset API can see data created in the previous session
    samples = dataset.query().order_by(OrderByField(ImageSampleField.file_path_abs).asc()).to_list()
    assert len(samples) == 2
    assert samples[0].file_path_abs == "image.png"
    assert samples[1].file_path_abs == "image2.png"


def test_close__removes_wal_and_allows_reconnect(
    tmp_path: Path,
    patch_engine_singleton: None,  # noqa ARG001
) -> None:
    """Test close removes WAL file and allows reconnecting to the database."""
    db_file = tmp_path / "test_close.db"
    db_manager.connect(db_file=str(db_file), cleanup_existing=True)

    with db_manager.session() as session:
        collection_id = create_collection(session=session).collection_id
        create_image(session=session, collection_id=collection_id, file_path_abs="image.png")

    wal_path = db_file.with_name(f"{db_file.name}.wal")

    db_manager.close()

    assert not wal_path.exists()

    db_manager.connect(db_file=str(db_file), cleanup_existing=False)
    db_manager.close()


def test_detect_backend_from_url() -> None:
    """Test backend detection for DuckDB URLs."""
    assert _detect_backend_from_url("duckdb:///test.db") == DatabaseBackend.DUCKDB
    assert (
        _detect_backend_from_url("postgresql://user:pass@localhost/db")
        == DatabaseBackend.POSTGRESQL
    )
    assert (
        _detect_backend_from_url("postgres://user:pass@localhost/db") == DatabaseBackend.POSTGRESQL
    )
    with pytest.raises(ValueError, match=r"Unsupported database URL scheme"):
        _detect_backend_from_url("mysql://localhost/db")


def test_database_engine__from_env_var(
    tmp_path: Path,
    mocker: MockerFixture,
    patch_engine_singleton: None,  # noqa: ARG001
) -> None:
    env_url = f"duckdb:///{tmp_path / 'env_test.db'}"
    mocker.patch.object(db_manager, "LIGHTLY_STUDIO_DATABASE_URL", env_url)

    engine = DatabaseEngine(single_threaded=True)
    assert engine._engine_url == env_url


def test_database_engine__explicit_url_over_env(
    tmp_path: Path,
    mocker: MockerFixture,
    patch_engine_singleton: None,  # noqa: ARG001
) -> None:
    env_url = f"duckdb:///{tmp_path / 'env_test.db'}"
    mocker.patch.object(db_manager, "LIGHTLY_STUDIO_DATABASE_URL", env_url)

    explicit_url = f"duckdb:///{tmp_path / 'explicit.db'}"
    engine = DatabaseEngine(engine_url=explicit_url, single_threaded=True)
    assert engine._engine_url == explicit_url


def test_connect__with_engine_url(
    tmp_path: Path,
    patch_engine_singleton: None,  # noqa: ARG001
) -> None:
    engine_url = f"duckdb:///{tmp_path / 'test.db'}"
    db_manager.connect(db_url=engine_url)

    engine = db_manager.get_engine()
    assert engine._engine_url == engine_url
    db_manager.close()


def test_connect__db_file_and_db_url_raises(
    patch_engine_singleton: None,  # noqa: ARG001
) -> None:
    with pytest.raises(ValueError, match=r"Cannot specify both db_file and db_url"):
        db_manager.connect(db_file="test.db", db_url="duckdb:///other.db")


def test_get_backend(
    tmp_path: Path,
    patch_engine_singleton: None,  # noqa: ARG001
) -> None:
    engine_url = f"duckdb:///{tmp_path / 'test.db'}"
    db_manager.connect(db_url=engine_url)

    assert db_manager.get_backend() == DatabaseBackend.DUCKDB
    db_manager.close()


def test_cleanup_postgres__drops_tables_when_cleanup_existing(
    mocker: MockerFixture,
) -> None:
    mock_create_engine = mocker.patch.object(db_manager, "create_engine")
    mock_engine = mock_create_engine.return_value
    mock_drop_all = mocker.patch.object(SQLModel.metadata, "drop_all")
    mocker.patch.object(SQLModel.metadata, "create_all")

    DatabaseEngine(
        engine_url="postgresql://user:pass@localhost:5432/testdb",
        cleanup_existing=True,
    )

    mock_drop_all.assert_called_once_with(bind=mock_engine)


def test_cleanup_postgres__no_drop_when_cleanup_existing_false(
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(db_manager, "create_engine")
    mock_drop_all = mocker.patch.object(SQLModel.metadata, "drop_all")
    mocker.patch.object(SQLModel.metadata, "create_all")

    DatabaseEngine(
        engine_url="postgresql://user:pass@localhost:5432/testdb",
        cleanup_existing=False,
    )

    mock_drop_all.assert_not_called()


def test_cleanup_postgres__integration(
    postgres_url: str | None,
) -> None:
    if postgres_url is None:
        pytest.skip("Requires --postgres flag")

    # Create an isolated database within the same Postgres container.
    base_url = sqlalchemy.make_url(postgres_url)
    cleanup_db_name = f"test_cleanup_{uuid4().hex}"
    cleanup_db_url = base_url.set(database=cleanup_db_name).render_as_string(hide_password=False)

    # AUTOCOMMIT required because Postgres forbids CREATE/DROP DATABASE inside a transaction.
    base_engine = sqlalchemy.create_engine(
        url=base_url.render_as_string(hide_password=False), isolation_level="AUTOCOMMIT"
    )
    with base_engine.connect() as conn:
        conn.execute(sqlalchemy.text(f"CREATE DATABASE {cleanup_db_name}"))

    engine: DatabaseEngine | None = None
    try:
        # 1. Create engine and insert a row.
        engine = DatabaseEngine(engine_url=cleanup_db_url, single_threaded=True)
        with engine.session() as session:
            create_collection(session=session, collection_name="should_be_deleted")
        engine.close()
        engine = None

        # 2. Re-create engine with cleanup_existing=True -> data should be wiped.
        engine = DatabaseEngine(
            engine_url=cleanup_db_url, cleanup_existing=True, single_threaded=True
        )
        with engine.session() as session:
            collections = session.exec(sqlmodel.select(CollectionTable)).all()
            assert len(collections) == 0
        engine.close()
        engine = None
    finally:
        if engine is not None:
            engine.close()
        with base_engine.connect() as conn:
            conn.execute(sqlalchemy.text(f"DROP DATABASE IF EXISTS {cleanup_db_name}"))
        base_engine.dispose()
