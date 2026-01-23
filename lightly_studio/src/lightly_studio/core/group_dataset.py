"""LightlyStudio GroupDataset."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from typing_extensions import Self

from lightly_studio import db_manager
from lightly_studio.core import dataset
from lightly_studio.core.dataset import DEFAULT_DATASET_NAME, Dataset
from lightly_studio.core.group_sample import GroupSample
from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.resolvers import collection_resolver, group_resolver
from lightly_studio.resolvers.collection_resolver.create_group_components import (
    GroupComponentDefinition,
)


class GroupDataset(Dataset[GroupSample]):
    """Group dataset.

    A dataset consisting of structured, homogenous samples. Each sample follows a specific
    schema defining its component keys and data types.

    A group dataset can be created as follows:
    ```python
    import lightly_studio as ls

    group_ds = ls.GroupDataset.create(
        components=[
            ("front", ls.SampleType.IMAGE),
            ("back", ls.SampleType.IMAGE),
        ]
    )
    ```
    Methods `GroupDataset.load()` and `GroupDataset.load_or_create()` are also available.

    TODO(Michal, 01/2026): Expand the docstring after samples can be loaded.
    """

    @staticmethod
    def sample_type() -> SampleType:
        """Returns the sample type."""
        return SampleType.GROUP

    @staticmethod
    def sample_class() -> type[GroupSample]:
        """Returns the sample class."""
        return GroupSample

    def get_sample(self, sample_id: UUID) -> GroupSample:
        """Get a single sample from the dataset by its ID.

        Args:
            sample_id: The UUID of the sample to retrieve.

        Returns:
            A single GroupSample object.

        Raises:
            IndexError: If no sample is found with the given sample_id.
        """
        sample = group_resolver.get_by_id(self.session, sample_id=sample_id)
        if sample is None:
            raise IndexError(f"No sample found for sample_id: {sample_id}")
        return GroupSample(inner=sample)

    @classmethod
    def create(
        cls, components: Sequence[GroupComponentDefinition], name: str | None = None
    ) -> Self:
        """Creates a new GroupDataset with the given schema definition for its components."""
        if name is None:
            name = DEFAULT_DATASET_NAME

        collection = collection_resolver.create(
            session=db_manager.persistent_session(),
            collection=CollectionCreate(name=name, sample_type=cls.sample_type()),
        )
        collection_resolver.create_group_components(
            session=db_manager.persistent_session(),
            parent_collection_id=collection.collection_id,
            components=components,
        )
        return cls(collection=collection)

    @classmethod
    def load(cls, name: str | None = None) -> Self:
        """Load an existing dataset."""
        collection = dataset.load_collection(name=name, sample_type=cls.sample_type())
        if collection is None:
            raise ValueError(f"Dataset with name '{name}' not found.")
        return cls(collection=collection)

    @classmethod
    def load_or_create(
        cls, components: Sequence[GroupComponentDefinition], name: str | None = None
    ) -> Self:
        """Create a new group dataset or load an existing one.

        If a dataset with the given name exists, its component schema is validated
        against the provided schema definition.

        Args:
            components: The schema definition for the dataset components as a list of tuples
                `(component_name: str, sample_type: SampleType)`.
            name: The name of the dataset. If None, a default name is used.
        """
        collection = dataset.load_collection(name=name, sample_type=cls.sample_type())
        if collection is None:
            return cls.create(components=components, name=name)

        # Validate that the existing collection has the same component schema.
        existing_components = collection_resolver.get_group_components(
            session=db_manager.persistent_session(),
            parent_collection_id=collection.collection_id,
        )
        if len(existing_components) != len(components):
            raise ValueError(
                f"Dataset with name '{name or DEFAULT_DATASET_NAME}' already exists with a "
                f"different number of components ({len(existing_components)} vs {len(components)})."
            )
        for key, sample_type in components:
            if (
                key not in existing_components
                or existing_components[key].sample_type != sample_type
            ):
                raise ValueError(
                    f"Dataset with name '{name or DEFAULT_DATASET_NAME}' already exists with a "
                    f"different component schema. Key '{key}' with type '{sample_type}' not found "
                    "in existing dataset."
                )

        return cls(collection=collection)
