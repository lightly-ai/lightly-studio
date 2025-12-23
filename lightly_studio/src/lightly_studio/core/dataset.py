"""LightlyStudio Dataset."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Generic, Iterator
from uuid import UUID

from sqlmodel import Session
from typing_extensions import Self, TypeVar

from lightly_studio import db_manager
from lightly_studio.api import features
from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.core.dataset_query.order_by import OrderByExpression
from lightly_studio.core.sample import Sample
from lightly_studio.dataset import embedding_utils, fsspec_lister
from lightly_studio.dataset.embedding_manager import EmbeddingManagerProvider
from lightly_studio.metadata import compute_similarity, compute_typicality
from lightly_studio.models.collection import CollectionCreate, CollectionTable, SampleType
from lightly_studio.resolvers import (
    collection_resolver,
    embedding_model_resolver,
    tag_resolver,
)

logger = logging.getLogger(__name__)

# Constants
DEFAULT_DATASET_NAME = "default_dataset"

_SliceType = slice  # to avoid shadowing built-in slice in type annotations


T = TypeVar("T", bound=Sample)


class Dataset(Generic[T], ABC):
    """A LightlyStudio Dataset.

    It can be created or loaded using one of the static methods:
    ```python
    dataset = Dataset.create()
    dataset = Dataset.load()
    dataset = Dataset.load_or_create()
    ```

    Samples can be added to the dataset using various methods:
    ```python
    dataset.add_images_from_path(...)
    dataset.add_samples_from_yolo(...)
    dataset.add_samples_from_coco(...)
    dataset.add_samples_from_coco_caption(...)
    dataset.add_samples_from_labelformat(...)
    dataset.add_videos_from_path(...)
    ```

    The dataset samples can be queried directly by iterating over it or slicing it:
    ```python
    dataset = Dataset.load("my_dataset")
    first_ten_samples = dataset[:10]
    for sample in dataset:
        print(sample.file_name)
        sample.metadata["new_key"] = "new_value"
    ```

    For filtering or ordering samples first, use the query interface:
    ```python
    from lightly_studio.core.dataset_query.sample_field import SampleField

    dataset = Dataset.load("my_dataset")
    query = dataset.match(SampleField.width > 10).order_by(SampleField.file_name)
    for sample in query:
        ...
    ```
    """

    def __init__(self, collection: CollectionTable) -> None:
        """Initialize a LightlyStudio Dataset."""
        self._inner = collection
        # TODO(Michal, 09/2025): Do not store the session. Instead, use the
        # dataset object session.
        self.session = db_manager.persistent_session()

    @staticmethod
    @abstractmethod
    def sample_type() -> SampleType:
        """Returns the sample type."""

    @staticmethod
    @abstractmethod
    def sample_class() -> type[T]:
        """Returns the sample class type."""

    @classmethod
    def create(cls, name: str | None = None) -> Self:
        """Create a new dataset.

        Args:
            name: The name of the dataset. If None, a default name is used.
        """
        if name is None:
            name = DEFAULT_DATASET_NAME

        collection = collection_resolver.create(
            session=db_manager.persistent_session(),
            collection=CollectionCreate(name=name, sample_type=cls.sample_type()),
        )
        return cls(collection=collection)

    @classmethod
    def load(cls, name: str | None = None) -> Self:
        """Load an existing dataset."""
        collection = load_collection(name=name, sample_type=cls.sample_type())
        if collection is None:
            raise ValueError(f"Dataset with name '{name}' not found.")
        return cls(collection=collection)

    @classmethod
    def load_or_create(cls, name: str | None = None) -> Self:
        """Create a new image dataset or load an existing one.

        Args:
            name: The name of the dataset. If None, a default name is used.
        """
        collection = load_collection(name=name, sample_type=cls.sample_type())
        if collection is None:
            return cls.create(name=name)
        return cls(collection=collection)

    def __iter__(self) -> Iterator[T]:
        """Iterate over samples in the dataset."""
        return self.query().__iter__()

    @abstractmethod
    def get_sample(self, sample_id: UUID) -> T:
        """Get a single sample from the dataset by its ID."""

    @property
    def dataset_id(self) -> UUID:
        """Get the dataset ID."""
        return self._inner.collection_id

    @property
    def name(self) -> str:
        """Get the dataset name."""
        return self._inner.name

    def query(self) -> DatasetQuery[T]:
        """Create a DatasetQuery for this dataset.

        Returns:
            A DatasetQuery instance for querying samples in this dataset.
        """
        return DatasetQuery(
            dataset=self._inner, session=self.session, sample_class=self.sample_class()
        )

    def match(self, match_expression: MatchExpression) -> DatasetQuery[T]:
        """Create a query on the dataset and store a field condition for filtering.

        Args:
            match_expression: Defines the filter.

        Returns:
            DatasetQuery for method chaining.
        """
        return self.query().match(match_expression)

    def order_by(self, *order_by: OrderByExpression) -> DatasetQuery[T]:
        """Create a query on the dataset and store ordering expressions.

        Args:
            order_by: One or more ordering expressions. They are applied in order.
                E.g. first ordering by sample width and then by sample file_name will
                only order the samples with the same sample width by file_name.

        Returns:
            DatasetQuery for method chaining.
        """
        return self.query().order_by(*order_by)

    def slice(self, offset: int = 0, limit: int | None = None) -> DatasetQuery[T]:
        """Create a query on the dataset and apply offset and limit to results.

        Args:
            offset: Number of items to skip from beginning (default: 0).
            limit: Maximum number of items to return (None = no limit).

        Returns:
            DatasetQuery for method chaining.
        """
        return self.query().slice(offset, limit)

    def __getitem__(self, key: _SliceType) -> DatasetQuery[T]:
        """Create a query on the dataset and enable bracket notation for slicing.

        Args:
            key: A slice object (e.g., [10:20], [:50], [100:]).

        Returns:
            DatasetQuery with slice applied.

        Raises:
            TypeError: If key is not a slice object.
            ValueError: If slice contains unsupported features or conflicts with existing slice.
        """
        return self.query()[key]

    def compute_typicality_metadata(
        self,
        embedding_model_name: str | None = None,
        metadata_name: str = "typicality",
    ) -> None:
        """Computes typicality from embeddings, for K nearest neighbors.

        Args:
            embedding_model_name:
                The name of the embedding model to use. If not given, the default
                embedding model is used.
            metadata_name:
                The name of the metadata to store the typicality values in. If not give, the default
                name "typicality" is used.
        """
        embedding_model_id = embedding_model_resolver.get_by_name(
            session=self.session,
            collection_id=self.dataset_id,
            embedding_model_name=embedding_model_name,
        ).embedding_model_id
        compute_typicality.compute_typicality_metadata(
            session=self.session,
            collection_id=self.dataset_id,
            embedding_model_id=embedding_model_id,
            metadata_name=metadata_name,
        )

    def compute_similarity_metadata(
        self,
        query_tag_name: str,
        embedding_model_name: str | None = None,
        metadata_name: str | None = None,
    ) -> str:
        """Computes similarity with respect to a query tag.

        Args:
            query_tag_name:
                The name of the tag to use for the query.
            embedding_model_name:
                The name of the embedding model to use. If not given, the default
                embedding model is used.
            metadata_name:
                The name of the metadata to store the similarity values in.
                If not given, a name is generated automatically.

        Returns:
            The name of the metadata storing the similarity values.
        """
        embedding_model_id = embedding_model_resolver.get_by_name(
            session=self.session,
            collection_id=self.dataset_id,
            embedding_model_name=embedding_model_name,
        ).embedding_model_id
        query_tag = tag_resolver.get_by_name(
            session=self.session, tag_name=query_tag_name, collection_id=self.dataset_id
        )
        if query_tag is None:
            raise ValueError("Query tag not found")
        return compute_similarity.compute_similarity_metadata(
            session=self.session,
            key_collection_id=self.dataset_id,
            embedding_model_id=embedding_model_id,
            query_tag_id=query_tag.tag_id,
            metadata_name=metadata_name,
        )


def load_collection(sample_type: SampleType, name: str | None = None) -> CollectionTable | None:
    """Load an existing collection.

    Args:
        name: The name of the dataset. If None, a default name is used.
        sample_type: The type of samples in the dataset. Defaults to SampleType.IMAGE.

    Return:
        A collection if it exists, or None if it doesn't.
    """
    if name is None:
        name = DEFAULT_DATASET_NAME

    collection = collection_resolver.get_by_name(session=db_manager.persistent_session(), name=name)
    if collection is None:
        return None

    # Dataset exists, verify the sample type matches.
    if collection.sample_type != sample_type:
        raise ValueError(
            f"Dataset with name '{name}' already exists with sample type "
            f"'{collection.sample_type.value}', but '{sample_type.value}' was requested."
        )

    # If we have embeddings in the database enable the FSC and embedding search features.
    _enable_embedding_features_if_available(
        session=db_manager.persistent_session(), dataset_id=collection.collection_id
    )
    return collection


def _mark_embedding_features_enabled() -> None:
    # Mark the embedding search feature as enabled.
    if "embeddingSearchEnabled" not in features.lightly_studio_active_features:
        features.lightly_studio_active_features.append("embeddingSearchEnabled")
    # Mark the FSC feature as enabled.
    if "fewShotClassifierEnabled" not in features.lightly_studio_active_features:
        features.lightly_studio_active_features.append("fewShotClassifierEnabled")


def _are_embeddings_available(session: Session, collection_id: UUID) -> bool:
    """Check if there are any embeddings available for the given dataset.

    Args:
        session: Database session for resolver operations.
        collection_id: The ID of the collection to check for embeddings.

    Returns:
        True if embeddings exist for the collection, False otherwise.
    """
    embedding_manager = EmbeddingManagerProvider.get_embedding_manager()
    model_id = embedding_manager.load_or_get_default_model(
        session=session,
        collection_id=collection_id,
    )
    if model_id is None:
        # No default embedding model loaded for this dataset.
        return False

    return (
        len(
            sample_embedding_resolver.get_all_by_collection_id(
                session=session, collection_id=collection_id, embedding_model_id=model_id
            )
        )
        > 0
    )


def _enable_embedding_features_if_available(session: Session, dataset_id: UUID) -> None:
    """Enable embedding-related features if embeddings are available in the DB.

    Args:
        session: Database session for resolver operations.
        dataset_id: The ID of the dataset to check for embeddings.
    """
    if embedding_utils.collection_has_embeddings(session=session, collection_id=dataset_id):
        if "embeddingSearchEnabled" not in features.lightly_studio_active_features:
            features.lightly_studio_active_features.append("embeddingSearchEnabled")
        if "fewShotClassifierEnabled" not in features.lightly_studio_active_features:
            features.lightly_studio_active_features.append("fewShotClassifierEnabled")
