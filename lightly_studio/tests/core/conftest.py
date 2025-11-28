"""Configuration of the tests."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from pytest_mock import MockerFixture

from lightly_studio import db_manager
from lightly_studio.api import features
from lightly_studio.dataset import embedding_manager
from lightly_studio.dataset.embedding_generator import RandomEmbeddingGenerator
from lightly_studio.dataset.embedding_manager import EmbeddingManager, EmbeddingManagerProvider


@pytest.fixture
def patch_dataset(
    mocker: MockerFixture,
) -> Generator[None, None, None]:
    """Fixture to patch the dataset resources."""
    # Create a mock database manager.
    mocker.patch.object(
        db_manager,
        "get_engine",
        return_value=db_manager.DatabaseEngine(
            engine_url="duckdb:///:memory:",
            single_threaded=True,
        ),
    )

    # Create a test-specific EmbeddingManager singleton.
    mocker.patch.object(
        EmbeddingManagerProvider,
        "get_embedding_manager",
        return_value=EmbeddingManager(),
    )

    # Fake the default embedding generator.
    mocker.patch.object(
        embedding_manager,
        "_load_embedding_generator_from_env",
        return_value=RandomEmbeddingGenerator(),
    )

    # Create test-specific lightly_studio_active_features.
    mocker.patch.object(features, "lightly_studio_active_features", [])

    yield  # noqa
