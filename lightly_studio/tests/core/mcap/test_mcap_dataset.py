from __future__ import annotations

import pytest

from lightly_studio.core.mcap.component import McapComponentSpec
from lightly_studio.core.mcap.mcap_dataset import McapDataset
from lightly_studio.database import db_manager
from lightly_studio.models.collection import SampleType
from lightly_studio.models.mcap_group_component_definition import McapDataType
from lightly_studio.resolvers import (
    collection_resolver,
    mcap_group_component_definition_resolver,
)
from tests.helpers_resolvers import create_collection

COMPONENTS = [
    McapComponentSpec(
        name="front",
        mcap_data_type=McapDataType.VIDEO_FRAME,
        topic="/cam/front/compressed_video",
        camera_info_topic="/cam/front/camera_info",
    ),
    McapComponentSpec(
        name="pcl_front",
        mcap_data_type=McapDataType.POINT_CLOUD,
        topic="/lidar/points",
        frame_id="livox_front_left",
    ),
]


class TestMcapDataset:
    def test_create(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        mcap_ds = McapDataset.create(components=COMPONENTS, name="perception")

        assert mcap_ds.name == "perception"
        assert mcap_ds._inner.sample_type == SampleType.SEQUENCE
        group_dataset = mcap_ds.group_dataset
        assert group_dataset.name == "perception_groups"
        components = collection_resolver.get_group_components(
            session=db_manager.persistent_session(),
            parent_collection_id=group_dataset.collection_id,
        )
        assert sorted(components) == ["front", "pcl_front"]
        assert components["front"].sample_type == SampleType.MCAP
        assert components["pcl_front"].sample_type == SampleType.MCAP

    def test_create__mcap_definitions(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        mcap_ds = McapDataset.create(components=COMPONENTS, name="perception")

        definitions = mcap_group_component_definition_resolver.get_all_by_group_collection_id(
            session=db_manager.persistent_session(),
            group_collection_id=mcap_ds.group_dataset.collection_id,
        )
        assert {definition.mcap_data_type for definition in definitions} == {
            McapDataType.VIDEO_FRAME,
            McapDataType.POINT_CLOUD,
        }
        # The channel and the frame are unknown until the first recording is indexed.
        assert all(definition.channel_id is None for definition in definitions)
        assert all(definition.frame_id is None for definition in definitions)

    def test_create__empty_components(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        with pytest.raises(ValueError, match="components must not be empty"):
            McapDataset.create(components=[], name="perception")

    def test_create__duplicate_component_name(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        with pytest.raises(
            ValueError,
            match=(
                r"components must not repeat a name\. These names are used more than once: "
                r"'front'\."
            ),
        ):
            McapDataset.create(components=_duplicate_name_components(), name="perception")

    def test_create__duplicate_component_name__nothing_written(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        with pytest.raises(ValueError, match="components must not repeat a name"):
            McapDataset.create(components=_duplicate_name_components(), name="perception")

        # The name stays free, so the call can be made again with corrected components.
        mcap_ds = McapDataset.create(components=COMPONENTS, name="perception")
        assert mcap_ds.name == "perception"

    def test_create__name_taken(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        McapDataset.create(components=COMPONENTS, name="perception")

        with pytest.raises(ValueError, match="A dataset named 'perception' already exists"):
            McapDataset.create(components=COMPONENTS, name="perception")

    def test_load(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        created = McapDataset.create(components=COMPONENTS, name="perception")

        loaded = McapDataset.load(name="perception")

        assert loaded.collection_id == created.collection_id
        assert loaded.dataset_id == created.dataset_id
        assert loaded.group_dataset.collection_id == created.group_dataset.collection_id

    def test_load__missing(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        with pytest.raises(ValueError, match="Dataset with name 'perception' not found"):
            McapDataset.load(name="perception")

    def test_load__wrong_sample_type(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        create_collection(
            session=db_manager.persistent_session(),
            sample_type=SampleType.IMAGE,
            collection_name="perception",
        )

        with pytest.raises(ValueError, match="already exists with sample type 'image'"):
            McapDataset.load(name="perception")

    def test_load_or_create(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        created = McapDataset.load_or_create(components=COMPONENTS, name="perception")

        loaded = McapDataset.load_or_create(components=COMPONENTS, name="perception")

        assert loaded.collection_id == created.collection_id

    def test_load_or_create__other_components(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        McapDataset.load_or_create(components=COMPONENTS, name="perception")

        with pytest.raises(
            ValueError,
            match=(
                r"already exists with the components \('front', 'video_frame'\), "
                r"\('pcl_front', 'point_cloud'\), but \('front', 'video_frame'\) were requested."
            ),
        ):
            McapDataset.load_or_create(components=[COMPONENTS[0]], name="perception")

    def test_load_or_create__other_component_order(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        McapDataset.load_or_create(components=COMPONENTS, name="perception")

        with pytest.raises(ValueError, match="already exists with the components"):
            McapDataset.load_or_create(components=list(reversed(COMPONENTS)), name="perception")

    def test_load_or_create__empty_components(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        with pytest.raises(ValueError, match="components must not be empty"):
            McapDataset.load_or_create(components=[], name="perception")

    def test_group_dataset(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        mcap_ds = McapDataset.create(components=COMPONENTS, name="perception")

        # The same object is returned on every access, so the components are looked up
        # against one collection.
        assert mcap_ds.group_dataset is mcap_ds.group_dataset
        assert mcap_ds.group_dataset.get_component("front").name == "front"

    def test_group_dataset__no_group_collection(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        collection = create_collection(
            session=db_manager.persistent_session(),
            sample_type=SampleType.SEQUENCE,
            collection_name="perception",
        )
        mcap_ds = McapDataset(collection=collection)

        with pytest.raises(RuntimeError, match="has no group collection"):
            mcap_ds.group_dataset  # noqa: B018


def _duplicate_name_components() -> list[McapComponentSpec]:
    """Return two components that use the same name."""
    return [
        McapComponentSpec(
            name="front",
            mcap_data_type=McapDataType.VIDEO_FRAME,
            topic="/cam/front/compressed_video",
        ),
        McapComponentSpec(
            name="front",
            mcap_data_type=McapDataType.POINT_CLOUD,
            topic="/lidar/points",
        ),
    ]
