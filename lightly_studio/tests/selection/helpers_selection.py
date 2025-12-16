"""Helpers for setting up the selection tests."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.image_sample import ImageSample
from lightly_studio.resolvers import collection_resolver
from tests.helpers_resolvers import (
    create_dataset,
    create_image,
)


def fill_db_with_samples_and_metadata(
    test_db: Session,
    metadata: list[Any],
    metadata_key: str,
) -> UUID:
    """Creates a dataset and fills it with sample and metadata."""
    dataset = create_dataset(test_db)
    for i, data in enumerate(metadata):
        image_table = create_image(
            session=test_db,
            dataset_id=dataset.collection_id,
            file_path_abs=f"sample_{i}.jpg",
        )
        sample = ImageSample(inner=image_table)
        sample.metadata[metadata_key] = data
    return dataset.collection_id


def fill_db_metadata(
    test_db: Session, dataset_id: UUID, metadata: list[Any], metadata_key: str
) -> None:
    """Fetches a dataset from the database and adds metadata to it."""
    dataset = collection_resolver.get_by_id(test_db, dataset_id)
    assert dataset is not None
    query = DatasetQuery(dataset, test_db)
    for data, sample in zip(metadata, query):
        sample.metadata[metadata_key] = data
