"""LightlyStudio VideoDataset."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from uuid import UUID

from typing_extensions import Self

from lightly_studio import db_manager
from lightly_studio.core.add_to_collection import AddToCollection
from lightly_studio.core.dataset import DEFAULT_DATASET_NAME, Dataset
from lightly_studio.core.group_sample import GroupSample
from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.resolvers import collection_resolver, group_resolver
from lightly_studio.resolvers.collection_resolver.create_group_components import (
    GroupComponentDefinition,
)

logger = logging.getLogger(__name__)


class GroupDataset(Dataset[GroupSample]):
    """TODO."""

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
            A single VideoSample object.

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
        """TODO."""
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

    def add_group_sample(
        self,
        components: dict[str, AddToCollection],
    ) -> GroupSample:
        """TODO."""
        comp_collections = collection_resolver.get_group_components(
            session=self.session,
            parent_collection_id=self.dataset_id,
        )
        # Validate components
        for comp_name, adder in components.items():
            if comp_name not in comp_collections:
                raise ValueError(
                    f"Component name '{comp_name}' not found in group dataset components."
                )
            if adder.sample_type() != comp_collections[comp_name].sample_type:
                raise ValueError(
                    f"Component '{comp_name}' expects samples of type "
                    f"'{comp_collections[comp_name].sample_type.name}', "
                    f"but got samples of type '{adder.sample_type().name}'."
                )
        # Create component samples
        component_sample_ids = {
            adder.add_to_collection(
                session=self.session, collection_id=comp_collections[comp_name].collection_id
            )
            for comp_name, adder in components.items()
        }
        # Create group sample
        group_sample_id = group_resolver.create_many(
            session=self.session,
            collection_id=self.dataset_id,
            groups=[component_sample_ids],
        )[0]

        # Return as GroupSample
        group_table = group_resolver.get_by_id(session=self.session, sample_id=group_sample_id)
        assert group_table is not None
        return GroupSample(inner=group_table)
