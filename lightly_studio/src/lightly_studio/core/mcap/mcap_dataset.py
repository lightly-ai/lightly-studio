"""LightlyStudio MCAP dataset."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from typing_extensions import Self

from lightly_studio.core import dataset
from lightly_studio.core.dataset import DEFAULT_DATASET_NAME
from lightly_studio.core.mcap import dataset_schema
from lightly_studio.core.mcap.component import McapComponentSpec
from lightly_studio.core.mcap.group_dataset import McapGroupDataset
from lightly_studio.database import db_manager
from lightly_studio.models.collection import CollectionTable, SampleType


class McapDataset:
    """A dataset of recordings, indexed from `.mcap` files.

    The components of the dataset are laid out once, and every recording added to it
    is read through the same ones, e.g. one camera and one lidar. A group holds one
    sample per component, all captured at about the same time, and a sequence puts the
    groups of one recording in the order they were recorded in:

    ```python
    import lightly_studio as ls

    dataset = ls.McapDataset.load_or_create(
        components=[
            ls.McapComponentSpec(
                name="front",
                mcap_data_type=ls.McapDataType.VIDEO_FRAME,
                topic="/cam/front/compressed_video",
                camera_info_topic="/cam/front/camera_info",
            ),
            ls.McapComponentSpec(
                name="pcl_front",
                mcap_data_type=ls.McapDataType.POINT_CLOUD,
                topic="/lidar/points",
                frame_id="livox_front_left",
            ),
        ],
        name="perception",
    )
    ```

    Methods `McapDataset.create()` and `McapDataset.load()` are also available.
    """

    def __init__(self, collection: CollectionTable) -> None:
        """Initialize the dataset.

        Args:
            collection: The root collection of the dataset, of type SEQUENCE.
        """
        self._inner = collection
        # TODO(Michal, 09/2025): Do not store the session. Instead, use the
        # dataset object session.
        self._session = db_manager.persistent_session()
        self._group_dataset: McapGroupDataset | None = None

    @classmethod
    def create(cls, components: Sequence[McapComponentSpec], name: str | None = None) -> Self:
        """Create a dataset for recordings, with the given components.

        Which MCAP channel a component is read from, and which coordinate frame its
        data is in, are not part of this call. They are read from the first recording
        that is indexed, with `McapComponent.update_mcap_definition`.

        Args:
            components: The components of the dataset, one spec per sensor.
            name: The name of the dataset. If None, a default name is used.

        Returns:
            The created dataset.

        Raises:
            ValueError: If `components` is empty, if two components have the same name,
                or if a dataset of that name exists.
        """
        if not components:
            raise ValueError("components must not be empty.")
        if name is None:
            name = DEFAULT_DATASET_NAME

        session = db_manager.persistent_session()
        root_collection, group_collection = dataset_schema.create_collections(
            session=session, name=name
        )
        dataset_schema.create_components(
            session=session,
            group_collection_id=group_collection.collection_id,
            components=components,
        )
        session.refresh(root_collection)
        return cls(collection=root_collection)

    @classmethod
    def load(cls, name: str | None = None) -> Self:
        """Load an MCAP dataset that exists.

        Args:
            name: The name of the dataset. If None, a default name is used.

        Returns:
            The dataset.

        Raises:
            ValueError: If no MCAP dataset of that name exists.
        """
        collection = dataset.load_root_collection(name=name, sample_type=SampleType.SEQUENCE)
        if collection is None:
            raise ValueError(f"Dataset with name '{name}' not found.")
        return cls(collection=collection)

    @classmethod
    def load_or_create(
        cls, components: Sequence[McapComponentSpec], name: str | None = None
    ) -> Self:
        """Create a dataset for recordings, or load the one of that name.

        Args:
            components: The components of the dataset, one spec per sensor. A dataset
                that exists must have exactly these names and data types, in this order.
            name: The name of the dataset. If None, a default name is used.

        Returns:
            The loaded or created dataset.

        Raises:
            ValueError: If `components` is empty, or if a dataset of that name exists
                with other components.
        """
        if not components:
            raise ValueError("components must not be empty.")
        collection = dataset.load_root_collection(name=name, sample_type=SampleType.SEQUENCE)
        if collection is None:
            return cls.create(components=components, name=name)

        mcap_dataset = cls(collection=collection)
        dataset_schema.check_components_match(
            session=db_manager.persistent_session(),
            group_collection_id=mcap_dataset.group_dataset.collection_id,
            components=components,
            dataset_name=collection.name,
        )
        return mcap_dataset

    @property
    def collection_id(self) -> UUID:
        """The ID of the root collection of the dataset."""
        return self._inner.collection_id

    @property
    def dataset_id(self) -> UUID:
        """The ID of the dataset."""
        return self._inner.dataset_id

    @property
    def name(self) -> str:
        """The name of the dataset."""
        return self._inner.name

    @property
    def group_dataset(self) -> McapGroupDataset:
        """The groups of the dataset, one per synchronized tick of a recording."""
        if self._group_dataset is None:
            self._group_dataset = McapGroupDataset(collection=self._group_collection())
        return self._group_dataset

    def _group_collection(self) -> CollectionTable:
        """Return the GROUP child collection holding the groups of the dataset.

        Raises:
            RuntimeError: If the dataset has no GROUP child collection.
        """
        for child in self._inner.children:
            if child.sample_type == SampleType.GROUP:
                return child
        raise RuntimeError(
            f"Dataset '{self.name}' has no group collection. It was not created with "
            "`McapDataset.create`."
        )
