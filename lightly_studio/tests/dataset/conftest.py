"""Configuration of the tests."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from pytest_mock import MockerFixture

from lightly_studio import db_manager
from lightly_studio.dataset import loader as loader_module
from lightly_studio.dataset.embedding_generator import RandomEmbeddingGenerator


@pytest.fixture
def patch_loader(
    mocker: MockerFixture,
) -> Generator[None, None, None]:
    """Fixture to patch the loader.

    Patches:
    - `db_manager` in the loader module
    - session in the EmbeddingManagerProvider
    - `_load_embedding_generator` to return a RandomEmbeddingGenerator
    """
    # Create a mock database manager.
    mocker.patch.object(
        db_manager,
        "get_engine",
        return_value=db_manager.DatabaseEngine("duckdb:///:memory:"),
    )

    # Patch the embedding generator to not use the real model.
    mocker.patch.object(
        loader_module,
        "_load_embedding_generator",
        return_value=RandomEmbeddingGenerator(),
    )

    yield  # noqa
