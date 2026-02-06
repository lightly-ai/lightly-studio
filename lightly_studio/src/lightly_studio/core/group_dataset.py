"""LightlyStudio GroupDataset."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID

from typing_extensions import Self

from lightly_studio import db_manager
from lightly_studio.core import dataset
from lightly_studio.core.create_sample import CreateSample
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
            ("thumbnail", ls.SampleType.IMAGE),
            ("video", ls.SampleType.VIDEO),
        ]
    )
    ```
    Methods `GroupDataset.load()` and `GroupDataset.load_or_create()` are also available.

    Group samples can be added to the dataset and inspected as follows:
    ```python
    group_sample = group_ds.add_group_sample(
        components={
            "thumbnail": ls.CreateImage(path="/path/to/thumbnail.jpg"),
            "video": ls.CreateVideo(path="/path/to/video.mp4"),
        }
    )

    # assert isinstance(group_sample["thumbnail"], ImageSample)
    # assert isinstance(group_sample["video"], VideoSample)
    print(group_sample["thumbnail"].file_name)
    print(group_sample["video"].duration_s)
    ```

    The dataset can be iterated over and sliced:
    ```python
    for group_sample in group_ds:
        ...

    for group_sample in group_ds[:10]:
        ...
    ```
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
                    f"different component schema. Key '{key}' with type '{sample_type.value}' "
                    "not found in existing dataset."
                )

        return cls(collection=collection)

    # TODO(Michal, 02/2026): Consider adding a batch version of this method.
    def add_group_sample(
        self,
        components: Mapping[str, CreateSample],
    ) -> GroupSample:
        """Add a group sample to the group dataset.

        Args:
            components: A mapping from component names to CreateSample instances.
                The component names must match the component schema of the group dataset.

        Returns:
            The created GroupSample.
        """
        comp_collections = collection_resolver.get_group_components(
            session=self.session,
            parent_collection_id=self.dataset_id,
        )
        # Validate components
        for comp_name, create_sample in components.items():
            if comp_name not in comp_collections:
                raise ValueError(
                    f"Component name '{comp_name}' not found in group dataset components."
                )
            if create_sample.sample_type() != comp_collections[comp_name].sample_type:
                raise ValueError(
                    f"Component '{comp_name}' expects samples of type "
                    f"'{comp_collections[comp_name].sample_type.name}', "
                    f"but got samples of type '{create_sample.sample_type().name}'."
                )
        # Create component samples after validation
        component_sample_ids = {
            create_sample.create_in_collection(
                session=self.session, collection_id=comp_collections[comp_name].collection_id
            )
            for comp_name, create_sample in components.items()
        }
        # Create group sample
        group_sample_id = group_resolver.create_many(
            session=self.session,
            collection_id=self.dataset_id,
            groups=[component_sample_ids],
        )[0]

        # Return as GroupSample
        group_table = group_resolver.get_by_id(session=self.session, sample_id=group_sample_id)
        if group_table is None:
            raise RuntimeError("Failed to retrieve the created group sample.")
        return GroupSample(inner=group_table)
