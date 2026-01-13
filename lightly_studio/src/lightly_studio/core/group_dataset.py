"""LightlyStudio VideoDataset."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from uuid import UUID

from typing_extensions import Self

from lightly_studio import db_manager
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
