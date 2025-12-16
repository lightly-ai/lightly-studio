# TODO(Michal, 09/2025): Add tests for:
# - DatabaseEngine
# - session
# - persistent_session
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from lightly_studio import Dataset, db_manager
from lightly_studio.core.dataset_query.order_by import OrderByField
from lightly_studio.core.dataset_query.sample_field import SampleField
from lightly_studio.db_manager import DatabaseEngine
from lightly_studio.resolvers import image_resolver
from tests.helpers_resolvers import (
    create_dataset,
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
    with pytest.raises(RuntimeError, match="Database engine is already set and cannot be changed."):
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
    with pytest.raises(RuntimeError, match="Database engine is already set and cannot be changed."):
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
        dataset_id = create_dataset(
            session=session, dataset_name="test_session_dataset"
        ).collection_id
        create_image(
            session=session,
            dataset_id=dataset_id,
            file_path_abs="image.png",
        )
        # Session commits automatically when exiting the context manager

    dataset = Dataset.load(name="test_session_dataset")

    # Verify the Dataset API can see the data created via database session.
    # It uses the persistent session.
    samples = dataset.query().to_list()
    assert len(samples) == 1
    assert samples[0].file_path_abs == "image.png"

    # Create another sample and verify cross-session data visibility
    with db_manager.session() as session:
        create_image(
            session=session,
            dataset_id=dataset.dataset_id,
            file_path_abs="image2.png",
        )
        samples_from_resolver = image_resolver.get_all_by_dataset_id(
            session=session, dataset_id=dataset.dataset_id
        ).samples
        assert len(samples_from_resolver) == 2

    # Verify the Dataset API can see data created in the previous session
    samples = dataset.query().order_by(OrderByField(SampleField.file_path_abs).asc()).to_list()
    assert len(samples) == 2
    assert samples[0].file_path_abs == "image.png"
    assert samples[1].file_path_abs == "image2.png"
